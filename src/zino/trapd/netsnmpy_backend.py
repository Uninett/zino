"""SNMP trap 'daemon' for Zino 2 implemented using netsnmp-cffi"""

import asyncio
import logging
from ipaddress import ip_address
from typing import Dict, Optional

from netsnmpy.netsnmp import SNMPVariable
from netsnmpy.trapsession import SNMPTrap, SNMPTrapSession

import zino.state
from zino.config.models import PollDevice
from zino.snmp.netsnmpy_backend import _convert_snmp_variable
from zino.trapd.base import (
    TrapMessage,
    TrapOriginator,
    TrapReceiverBase,
    TrapVarBind,
)

_logger = logging.getLogger(__name__)


class TrapReceiver(TrapReceiverBase):
    """Zino Adapter for SNMP trap reception using netsnmp-cffi.

    Zino 1 accepts traps with any community string, as long as its origin is any one of the devices configured in
    the pollfile.  The PySNMP back-end will only accept traps with one of the configured community strings.  *This*
    back-end, however, will accept and pass on traps with any community string until `add_community()` is called
    to configure at least one filter.
    """

    def __init__(
        self,
        address: str = "0.0.0.0",
        port: int = 162,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        state: Optional[zino.state.ZinoState] = None,
        polldevs: Optional[Dict[str, PollDevice]] = None,
    ):
        super().__init__(address, port, loop, state, polldevs)
        self._session = SNMPTrapSession(ip_address(address), port)

    async def open(self):
        """Opens the UDP transport socket and starts receiving traps"""
        self._session.add_observer(self.trap_received)
        self._session.open()
        _logger.info("Listening for incoming SNMP traps on %r", (self.address, self.port))

    def close(self):
        """Closes the running SNMP engine and its associated ports"""
        self._session.close()

    def trap_received(self, trap: SNMPTrap):
        """Callback function that receives all trap messages from the Net-SNMP transport"""
        router = self._lookup_device(trap.source)
        # netsnmpy doesn't currently provide the source port:
        origin = TrapOriginator(address=trap.source, port=None, device=router)
        if not self._verify_trap(trap, origin):
            return

        _logger.debug("Trap from %s (%s)", router.name, trap.source)

        zino_trap = TrapMessage(agent=origin)
        for variable in trap.variables:
            _logger.debug("%s", variable)
            try:
                identifier, value = _convert_snmp_variable(variable)
            except ValueError:
                _logger.error(
                    "Could not resolve SNMP variable %s: %s (Maybe MIB not loaded?)", variable, variable.value
                )
                return

            # This should really be part of netsnmp-cffi, but it isn't currently
            raw_value = value = variable.value
            enum_value = variable.enum_value
            if enum_value:
                value = enum_value
            elif variable.textual_convention == "DisplayString":
                value = variable.value.decode("utf-8")

            zino_trap.variables.append(
                TrapVarBind(variable.oid, identifier.mib, identifier.object, identifier.index, raw_value, value)
            )

        # TODO do some time calculations, but ask Håvard what the deal is with RestartTime vs. BootTime

        if trap.trap_oid:
            try:
                trap_identifier, _ = _convert_snmp_variable(SNMPVariable(trap.trap_oid, None))
            except ValueError:
                _logger.error("Could not resolve trap OID %s (Maybe MIB not loaded?)", trap.trap_oid)
                return
            zino_trap.mib, zino_trap.name = trap_identifier.mib, trap_identifier.object
            _logger.debug("Trap from %s identified as %r", trap.source, trap_identifier)
        asyncio.ensure_future(self.dispatch_trap(zino_trap))

    def _verify_trap(self, netsnmp_trap: SNMPTrap, origin: TrapOriginator) -> bool:
        if not origin.device:
            _logger.debug("ignored trap from %s (not a box we monitor?)", origin.address)
            return False

        source_name = origin.device.name or origin.address

        if self._communities and netsnmp_trap.community not in self._communities:
            _logger.info("Trap from %s with unknown community string %r, ignoring", source_name, netsnmp_trap.community)
            return False

        if not netsnmp_trap.trap_oid:
            _logger.info("Trap from %s did not contain a snmpTrapOID value, ignoring", source_name)
            return False

        if not netsnmp_trap.uptime:
            _logger.info("Trap from %s did not contain a sysUpTime value, ignoring", source_name)
            return False

        return True
