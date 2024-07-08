"""This module implements custom logging of certain SNMP traps, but takes no other action"""

import logging
from typing import Optional

from zino.trapd import TrapMessage, TrapObserver

_logger = logging.getLogger(__name__)


class RestartTrapLogger(TrapObserver):
    WANTED_TRAPS = {
        ("SNMPv2-MIB", "coldStart"),
        ("SNMPv2-MIB", "warmStart"),
    }

    async def handle_trap(self, trap: TrapMessage) -> Optional[bool]:
        _logger.info("%s: %s", trap.agent.device.name, trap.name)
        return False  # stop trap processing here
