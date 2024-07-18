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


class CiscoReloadTrapLogger(TrapObserver):
    WANTED_TRAPS = {
        ("CISCOTRAP-MIB", "reload"),
    }

    async def handle_trap(self, trap: TrapMessage) -> Optional[bool]:
        _logger.info("%s: reload requested", trap.agent.device.name)
        return False  # stop trap processing here


class CiscoConfigManEventLogger(TrapObserver):
    WANTED_TRAPS = {
        ("CISCO-CONFIG-MAN", "ciscoConfigManEvent"),
    }

    async def handle_trap(self, trap: TrapMessage) -> Optional[bool]:
        _logger.info(
            "%s: config-change: cmd-src %s conf-src %s dst %s",
            trap.agent.device.name,
            *[
                trap.get_all(var)[0].value if var in trap else None
                for var in (
                    "ccmHistoryEventCommandSource",
                    "ccmHistoryEventConfigSource",
                    "ccmHistoryEventConfigDestination",
                )
            ],
        )

        return False  # stop trap processing here
