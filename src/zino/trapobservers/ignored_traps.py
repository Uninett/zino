"""This module implements a trap observer to ignore spammy traps"""

import logging
from typing import Optional, Set

from zino.trapd import TrapMessage, TrapObserver, TrapType

_logger = logging.getLogger(__name__)


class IgnoreTraps(TrapObserver):
    """Completely ignores spammy traps observed in Uninett, that we don't care about"""

    WANTED_TRAPS: Set[TrapType] = {
        ("BGP4-MIB", "bgpBackwardTransition"),
        ("BGP4-MIB", "bgpBackwardTransNotification"),
        ("BGP4-V2-MIB-JUNIPER", "jnxBgpM2BackwardTransition"),
        ("SNMPv2-MIB", "authenticationFailure"),
        ("CISCOTRAP-MIB", "tcpConnectionClose"),
    }

    def handle_trap(self, trap: TrapMessage) -> Optional[bool]:
        return False  # Stop processing here!
