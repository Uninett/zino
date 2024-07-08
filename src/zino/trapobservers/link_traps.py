"""This module implements link trap handling"""

import logging
import re
from datetime import datetime, timedelta
from typing import Optional, Tuple

import zino.time
from zino.statemodels import DeviceState, InterfaceState, Port, PortStateEvent
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
        self._last_same_trap: dict[Tuple[str, int], datetime] = {}

    async def handle_trap(self, trap: TrapMessage) -> Optional[bool]:
        _logger.debug("%s: %s (vars: %s)", trap.agent.device.name, trap.name, ", ".join(v.var for v in trap.variables))

        if "ifIndex" in trap:
            ifindex = trap.get_all("ifIndex")[0].value
        else:
            _logger.warning("%s: %s trap contained no ifIndex value, ignoring", trap.agent.device.name, trap.name)
            return False
        port = trap.agent.device.ports.get(ifindex) if ifindex > 0 else None
        if not port:
            _logger.warning(
                "%s: %s trap referenced unknown port (ix %s), ignoring", trap.agent.device.name, trap.name, ifindex
            )
            return False

        # TODO: The trap *might* contain an ifDescr value.  If present, Zino uses that for trap processing.
        #  Otherwise, it fetches ifDescr from its own state and uses that for trap processing.  Either way,
        #  there seems to be some redundancy. We should document why, or change the behavior in Zino 2

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
        self.update_interface_flapping_score(index)

        new_state = InterfaceState.UP if is_up else InterfaceState.DOWN

        if self.is_interface_flapping(index):
            # TODO: if event doesn't exist, create it
            # TODO: Record new number of flaps in event
            # TODO: When flapcount modulo 100 is zero, log a message with flapping stats
            pass
        else:
            event: PortStateEvent = self.state.events.get_or_create_event(device.name, port.ifindex, PortStateEvent)

            event.portstate = new_state
            event.port = port.ifdescr
            event.ifindex = port.ifindex
            port.state = new_state
            if polldev := self.polldevs.get(device.name):
                event.polladdr = polldev.address
                event.priority = polldev.priority
            event.descr = port.ifalias  # or value received from trap? see ldescr from legacy Zino

            # TODO: If there is internal flapping state, log it in the event and clear internal state
            # TODO: Set final flapcount in event

            msg = f'{device.name}: intf "{port.ifdescr}" ix {port.ifindex} link{new_state.capitalize()}'
            if reason:
                event.reason = reason
                msg = f'{msg}, "{reason}"'
            _logger.info(msg)
            event.add_log(msg)
            self.state.events.commit(event)

            poll = LinkStateTask(device=polldev, state=self.state)
            poll.schedule_verification_of_single_port(port.ifindex, deadline=FIRST_REVERIFICATION, reason="trap-verify")
            poll.schedule_verification_of_single_port(
                port.ifindex, deadline=SECOND_REVERIFICATION, reason="trap-verify-2"
            )

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

    def update_interface_flapping_score(self, index: Tuple[str, int]) -> bool:
        """Updates the running flapping score for a given port"""
        return False  # stub implementation, see Zino 1 `proc intfFlap`

    def is_interface_flapping(self, index: Tuple[str, int]) -> bool:
        """Determines if a given port is flapping"""
        return False  # stub implementation, see Zino 1 `proc flapping`

    def get_watch_pattern(self, device: DeviceState) -> Optional[str]:
        if device.name not in self.polldevs:
            return None
        return self.polldevs[device.name].watchpat

    def get_ignore_pattern(self, device: DeviceState) -> Optional[str]:
        if device.name not in self.polldevs:
            return None
        return self.polldevs[device.name].ignorepat
