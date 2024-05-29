"""This module implements link trap handling"""

import logging
from typing import Optional

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

        _logger.debug("handle_link_transition: device=%r port=%r is_up=%r", device, port, is_up)
