"""This module implements link trap handling"""

import logging
import re
from typing import Optional, Tuple

from zino.statemodels import DeviceState, Port
from zino.trapd import TrapMessage, TrapObserver

_logger = logging.getLogger(__name__)


class LinkTrapObserver(TrapObserver):
    WANTED_TRAPS = {
        ("IF-MIB", "linkUp"),
        ("IF-MIB", "linkDown"),
    }

    def handle_trap(self, trap: TrapMessage) -> Optional[bool]:
        _logger.debug("%s: %s (vars: %s)", trap.agent.device.name, trap.name, ", ".join(trap.variables))

        if "ifIndex" in trap.variables:
            ifindex = trap.variables.get("ifIndex").value
        else:
            ifindex = -1
        port = trap.agent.device.ports.get(ifindex) if ifindex > 0 else None

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

        if self.is_port_ignored_by_rules(device, port):
            return

        index = (device.name, port.ifindex)
        self.update_interface_flapping_score(index)

        if self.is_interface_flapping(index):
            # TODO: if event doesn't exist, create it
            # TODO: Record new number of flaps in event
            # TODO: When flapcount modulo 100 is zero, log a message with flapping stats
            pass
        else:
            # TODO: Create an event to log the trap message anyway, setting flap state to stable and clearing
            #  internal flap state
            # TODO: Poll single interface immediately to verify state change
            # TODO: Schedule another single interface poll in two minutes
            pass

    def is_port_ignored_by_patterns(self, device: DeviceState, ifdescr: str) -> bool:
        if watch_pattern := self.get_watch_pattern(device):
            if not re.match(watch_pattern, ifdescr):
                return True

        if ignore_pattern := self.get_ignore_pattern(device):
            if re.match(ignore_pattern, ifdescr):
                return True

        return False

    def is_port_ignored_by_rules(self, device: DeviceState, port: Port) -> bool:
        """ignoreTrap in Zino 1 is described thus:

        Should we ignore this trap message?
        If there's an open case for this router port, no.
        If received right after reload, yes.
        If state reported is the same as the one we have recorded,
        and a new trap does not reoccur within 5 minutes, yes.
        Otherwise, don't ignore the trap message.
        """
        return False  # stub implementation

    def update_interface_flapping_score(self, index: Tuple[str, int]) -> bool:
        """Updates the running flapping score for a given port"""
        pass  # stub implementation, see Zino 1 `proc intfFlap`

    def is_interface_flapping(self, index: Tuple[str, int]) -> bool:
        """Determines if a given port is flapping"""
        return False  # stub implementation, see Zino 1 `proc flapping`

    def get_watch_pattern(self, device: DeviceState) -> Optional[str]:
        from zino.state import polldevs

        if device.name not in polldevs:
            return None
        return polldevs[device.name].watchpat

    def get_ignore_pattern(self, device: DeviceState) -> Optional[str]:
        from zino.state import polldevs

        if device.name not in polldevs:
            return None
        return polldevs[device.name].ignorepat
