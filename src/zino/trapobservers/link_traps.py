"""This module implements link trap handling"""

import logging
import re
from datetime import datetime, timedelta
from typing import Optional

import zino.time
from zino.flaps import PortIndex
from zino.statemodels import (
    DeviceState,
    FlapState,
    InterfaceState,
    Port,
    PortStateEvent,
)
from zino.tasks.linkstatetask import LinkStateTask
from zino.trapd import TrapMessage, TrapObserver

_logger = logging.getLogger(__name__)
TRAP_WINDOW = timedelta(minutes=5)
IMMEDIATELY = timedelta(seconds=0)
FIRST_REVERIFICATION = IMMEDIATELY
SECOND_REVERIFICATION = timedelta(minutes=2)


class LinkTrapObserver(TrapObserver):
    WANTED_TRAPS = {
        ("IF-MIB", "linkUp"),
        ("IF-MIB", "linkDown"),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_same_trap: dict[PortIndex, datetime] = {}

    def handle_trap(self, trap: TrapMessage) -> Optional[bool]:
        _logger.debug("%s: %s (vars: %s)", trap.agent.device.name, trap.name, ", ".join(trap.variables))

        if "ifIndex" in trap.variables:
            ifindex = trap.variables.get("ifIndex").value
        else:
            _logger.warning("%s: %s trap contained no ifIndex value, ignoring", trap.agent.device.name, trap.name)
            return False
        port = trap.agent.device.ports.get(ifindex) if ifindex > 0 else None
        if not port:
            _logger.warning(
                "%s: %s trap referenced unknown port (ix %s), ignoring", trap.agent.device.name, trap.name, ifindex
            )
            return False

        # The legacy Zino also looks for `locIfDescr` in the trap at this point, but this is an ancient
        # Cisco-specific variable we no longer see.  It might have been replaced by `cieIfOperStatusCause`,
        # but we have no more Cisco devices to test on, so this has been deliberately left out.

        is_up = trap.name == "linkUp"
        self.handle_link_transition(trap.agent.device, port, is_up)

    def handle_link_transition(self, device: DeviceState, port: Port, is_up: bool, reason: Optional[str] = None):
        """This method is called when a linkUp or linkDown trap is received, and updates event state accordingly -
        including the logic for handling flapping states.
        """
        if self.is_port_ignored_by_patterns(device, port.ifdescr):
            return

        # At this point, legacy Zino would ignore so-called "insignificant" interfaces.  As mentioned in the
        # LinkStateTask docstring, this concept has deliberately not been ported to Zino 2.

        _logger.debug(
            "%s: intf %s ix %d link%s%s",
            device.name,
            port.ifdescr,
            port.ifindex,
            "Up" if is_up else "Down",
            f", {reason}" if reason else "",
        )

        if self.is_port_ignored_by_policy(device, port, is_up):
            return

        index = (device.name, port.ifindex)
        flap = self.state.flapping.update_interface_flap(index)

        new_state = InterfaceState.UP if is_up else InterfaceState.DOWN

        if flap.is_flapping():
            if not flap.in_active_flap_state:
                event = self.get_flapping_event(device, index, new_state, port, reason)
            else:
                event = self.state.events.get(device.name, port.ifindex, PortStateEvent)

            if event:
                # Update the event flap count, but explicitly DO NOT commit the change here, as committing during
                # flap storms would cause a notification storm as well
                event.flaps = flap.flaps

            if flap.flaps % 100 == 0:
                _logger.info(
                    '%s: intf "%s" ix %d (%s), %d flaps, penalty %5.2f',
                    device.name,
                    port.ifdescr,
                    port.ifindex,
                    port.ifalias,
                    flap.flaps,
                    flap.hist_val,
                )
        else:
            self.get_non_flapping_event(device, index, new_state, port, reason)

    def get_flapping_event(
        self, device: DeviceState, interface: PortIndex, new_state: InterfaceState, port: Port, reason: Optional[str]
    ) -> PortStateEvent:
        """Opens or returns an existing portstate event for a port that was not previously known to be flapping.

        It also updates the flap state of the port to indicate it is currently in a flapping state.
        """
        event = self.open_portstate_event(device, new_state, port, reason)

        flap = self.state.flapping.interfaces[interface]
        event.flapstate = FlapState.FLAPPING
        event.flaps = flap.flaps
        msg = (
            f'{device.name}: intf "{port.ifdescr}" ix {port.ifindex} ({port.ifalias}) flapping, '
            f"{event.flaps} flaps, penalty {flap.hist_val:.2f}"
        )
        _logger.info(msg)
        event.add_log(msg)
        self.state.events.commit(event)
        flap.in_active_flap_state = True
        return event

    def get_non_flapping_event(
        self, device: DeviceState, interface: PortIndex, new_state: InterfaceState, port: Port, reason: Optional[str]
    ) -> PortStateEvent:
        """Opens or returns an existing portstate event for a port that isn't currently flapping.

        It also removes the recorded flap stats for the port if was previously known to be in a flapping state.
        """
        event = self.open_portstate_event(device, new_state, port, reason)

        if flap := self.state.flapping.interfaces.get(interface):
            event.flaps = flap.flaps
            if flap.in_active_flap_state:
                event.flapstate = FlapState.STABLE
                msg = f'{device.name}: intf "{port.ifdescr}" ix {port.ifindex} ({port.ifalias}) stopped flapping'
                _logger.info(msg)
                event.add_log(msg)
                self.state.flapping.unflap(interface)

        msg = f'{device.name}: intf "{port.ifdescr}" ix {port.ifindex} link{new_state.capitalize()}'
        if reason:
            msg = f'{msg}, "{reason}"'
        _logger.info(msg)
        event.add_log(msg)
        self.state.events.commit(event)

        if polldev := self.polldevs.get(device.name):
            poll = LinkStateTask(device=polldev, state=self.state)
            poll.schedule_verification_of_single_port(port.ifindex, deadline=FIRST_REVERIFICATION, reason="trap-verify")
            poll.schedule_verification_of_single_port(
                port.ifindex, deadline=SECOND_REVERIFICATION, reason="trap-verify-2"
            )
        else:
            _logger.warning("No polldev config found for %s", device.name)

        return event

    def open_portstate_event(
        self, device: DeviceState, new_state: InterfaceState, port: Port, reason: Optional[str]
    ) -> PortStateEvent:
        """Opens or returns an open port state event for the port referenced in an incoming trap message"""
        event = self.state.events.get_or_create_event(device.name, port.ifindex, PortStateEvent)
        event.portstate = new_state
        event.port = port.ifdescr
        event.ifindex = port.ifindex
        port.state = new_state
        if polldev := self.polldevs.get(device.name):
            event.polladdr = polldev.address
            event.priority = polldev.priority
        event.descr = port.ifalias
        if reason:
            event.reason = reason
        return event

    def is_port_ignored_by_patterns(self, device: DeviceState, ifdescr: str) -> bool:
        if watch_pattern := self.get_watch_pattern(device):
            if not re.match(watch_pattern, ifdescr):
                return True

        if ignore_pattern := self.get_ignore_pattern(device):
            if re.match(ignore_pattern, ifdescr):
                return True

        return False

    def is_port_ignored_by_policy(self, device: DeviceState, port: Port, is_up: bool) -> bool:
        """Verifies that a link trap should be ignored, according to internal policies.

        As commented in the original Zino 1 implementation:

        > Should we ignore this trap message?
        > If there's an open case for this router port, no.
        > If received right after reload, yes.
        > If state reported is the same as the one we have recorded,
        > and a new trap does not reoccur within 5 minutes, yes.
        > Otherwise, don't ignore the trap message.
        """
        now = zino.time.now()

        # If there is an open case for router/port, do not ignore
        if self.state.events.get(device.name, subindex=port.ifindex, event_class=PortStateEvent):
            return False

        # If we don't know that the device restarted recently, do not ignore
        if not device.boot_time:
            _logger.info("Oops! Do not know restart time for %s", device.name)
            return False

        if not port.state:
            port.state = InterfaceState.UNKNOWN

        if now - device.boot_time > TRAP_WINDOW:
            # Do not ignore traps indicating different state than known
            current_state = InterfaceState.UP if is_up else InterfaceState.DOWN
            if port.state != current_state:
                return False

            # Do not ignore successive traps within a TRAP_WINDOW interval indicating same state as previously known
            index = (device.name, port.ifindex)
            if last_same_trap := self._last_same_trap.get(index):
                if now - last_same_trap < TRAP_WINDOW:
                    self._last_same_trap[index] = now
                    return False
            self._last_same_trap[index] = now

        # Ignoring traps the first 5 minutes after restart
        _logger.info(
            "Ignored %s trap for %s ix %s (state %s), restarted %s",
            "Up" if is_up else "Down",
            device.name,
            port.ifindex,
            port.state,
            device.boot_time.astimezone(),
        )
        return True

    def get_watch_pattern(self, device: DeviceState) -> Optional[str]:
        if device.name not in self.polldevs:
            return None
        return self.polldevs[device.name].watchpat

    def get_ignore_pattern(self, device: DeviceState) -> Optional[str]:
        if device.name not in self.polldevs:
            return None
        return self.polldevs[device.name].ignorepat
