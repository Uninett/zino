"""This module implements custom logging of certain SNMP traps, but takes no other action"""

import logging
from ipaddress import ip_address
from typing import Optional

from zino.trapd.base import TrapMessage, TrapObserver

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


class CiscoPimTrapLogger(TrapObserver):
    """Logs details of Cisco PIM traps.

    Example of manually generating a matching trap with test data:

          snmptrap -v 2c -c public localhost:1162 "" \
               CISCO-PIM-MIB::ciscoPimInvalidRegister \
               CISCO-PIM-MIB::cpimLastErrorOriginType i 1 \
               CISCO-PIM-MIB::cpimLastErrorOrigin x "0A000001" \
               CISCO-PIM-MIB::cpimLastErrorGroupType i 1 \
               CISCO-PIM-MIB::cpimLastErrorGroup x "0A000002" \
               CISCO-PIM-MIB::cpimLastErrorRPType i 1 \
               CISCO-PIM-MIB::cpimLastErrorRP  x "0A000003" \
               CISCO-PIM-MIB::cpimInvalidRegisterMsgsRcvd c 42
    """

    WANTED_TRAPS = {
        ("CISCO-PIM-MIB", "ciscoPimInvalidRegister"),
        ("CISCO-PIM-MIB", "ciscoPimInvalidJoinPrune"),
    }

    async def handle_trap(self, trap: TrapMessage) -> Optional[bool]:
        if "cpimLastErrorOriginType" not in trap:
            return False

        if trap.get_all("cpimLastErrorOriginType")[0].value != "ipv4":
            return False

        origin = ip_address(bytes(trap.get_all("cpimLastErrorOrigin")[0].raw_value))
        group = ip_address(bytes(trap.get_all("cpimLastErrorGroup")[0].raw_value))
        rp = ip_address(bytes(trap.get_all("cpimLastErrorRP")[0].raw_value))

        trap_type = "register" if trap.name.endswith("Register") else "join-prune"
        _logger.info(
            "%s PIM-invalid-%s: from %s group %s RP %s",
            trap.agent.device.name,
            trap_type,
            origin,
            group,
            rp,
        )

        return False  # stop trap processing here


class OspfIfConfigErrorLogger(TrapObserver):
    """Logs all ospfIfConfigError trap variables prefixed by 'ospf*'"""

    WANTED_TRAPS = {
        ("OSPF-MIB", "ospfIfConfigError"),
    }

    async def handle_trap(self, trap: TrapMessage) -> Optional[bool]:
        _logger.info("%s: trap %s", trap.agent.device.name, trap.get_all("snmpTrapOID")[0].value)

        for var in trap.variables:
            if var.var.startswith("ospf"):
                _logger.info("%s: trap-var %s: %s", trap.agent.device.name, var.var, var.value)

        return False  # stop trap processing here
