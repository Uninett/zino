"""SNMP trap 'daemon' for Zino 2"""
import asyncio
import logging

from pysnmp.carrier.asyncio.dgram import udp
from pysnmp.entity import config, engine
from pysnmp.entity.rfc3413 import ntfrcv

_logger = logging.getLogger(__name__)


class TrapReceiver:
    """Zino Adapter for SNMP trap reception using PySNMP"""

    def __init__(self, address: str = "0.0.0.0", port: int = 162, loop=None):
        self.transport = None
        self.address = address
        self.port = port
        self.loop = loop if loop else asyncio.get_event_loop()
        self.snmp_engine = engine.SnmpEngine()
        self._communities = set()

    async def open(self):
        self.transport = udp.UdpTransport(loop=self.loop).openServerMode((self.address, self.port))
        # This attribute needs to be awaited to ensure the socket is really opened,
        # unsure of why PySNMP doesn't do this, or how else it's supposed to be achieved
        await self.transport._lport
        _logger.info("Listening for incoming SNMP traps on %r", (self.address, self.port))
        config.addTransport(self.snmp_engine, udp.domainName + (1,), self.transport)

        ntfrcv.NotificationReceiver(self.snmp_engine, self.trap_received)
        self.snmp_engine.transportDispatcher.jobStarted(1)  # this job would never finish

    def add_community(self, community: str):
        """Adds a new community string that will be accepted on incoming packets"""
        if community in self._communities:
            return
        self._communities.add(community)
        config.addV1System(self.snmp_engine, str(len(self._communities)), community)

    def trap_received(self, snmp_engine, state_reference, context_engine_id, context_name, var_binds, callback_context):
        _logger.info(
            'Trap from ContextEngineId "%s", ContextName "%s"',
            context_engine_id.prettyPrint(),
            context_name.prettyPrint(),
        )
        for name, val in var_binds:
            _logger.info("%s = %s", name.prettyPrint(), val.prettyPrint())
