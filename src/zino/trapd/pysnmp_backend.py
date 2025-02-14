"""SNMP trap 'daemon' for Zino 2"""

import asyncio
import logging
from ipaddress import ip_address
from typing import Dict, Optional

from pyasn1.type.base import SimpleAsn1Type
from pysnmp.carrier.asyncio.dgram import udp
from pysnmp.entity import config
from pysnmp.entity.rfc3413 import ntfrcv
from pysnmp.proto.rfc1902 import ObjectName
from pysnmp.smi import view
from pysnmp.smi.rfc1902 import ObjectIdentity, ObjectType

import zino.state
from zino.config.models import PollDevice
from zino.oid import OID
from zino.snmp.pysnmp_backend import get_new_snmp_engine, mib_value_to_python
from zino.trapd.base import (
    TrapMessage,
    TrapOriginator,
    TrapReceiverBase,
    TrapVarBind,
)

_logger = logging.getLogger(__name__)


class TrapReceiver(TrapReceiverBase):
    """Zino Adapter for SNMP trap reception using PySNMP.

    A major difference to Zino 1 is that this receiver must explicitly be configured with SNMP community strings that
    will be accepted.  Zino 1 accepts traps with any community string, as long as their origin is any one of the
    devices configured in the pollfile.  However, PySNMP places heavy emphasis on being standards compliant,
    and will not even pass on traps to our callbacks unless they match the authorization config for the SNMP engine.
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
        self.snmp_engine = get_new_snmp_engine()

    async def open(self):
        """Opens the UDP transport socket and starts receiving traps"""
        self.transport = udp.UdpTransport(loop=self.loop).openServerMode((self.address, self.port))
        # This attribute needs to be awaited to ensure the socket is really opened,
        # unsure of why PySNMP doesn't do this, or how else it's supposed to be achieved
        await self.transport._lport
        _logger.info("Listening for incoming SNMP traps on %r", (self.address, self.port))
        config.addTransport(self.snmp_engine, udp.domainName + (1,), self.transport)

        ntfrcv.NotificationReceiver(self.snmp_engine, self.trap_received)
        self.snmp_engine.transportDispatcher.jobStarted(1)  # this job would never finish

    def close(self):
        """Closes the running SNMP engine and its associated ports"""
        self.snmp_engine.transportDispatcher.closeDispatcher()
        self.transport.closeTransport()

    def add_community(self, community: str):
        """Adds a new community string that will be accepted on incoming packets"""
        super().add_community(community)
        config.addV1System(self.snmp_engine, str(len(self._communities)), community)

    def trap_received(self, snmp_engine, state_reference, context_engine_id, context_name, var_binds, callback_context):
        """Callback function that receives all matched trap messages on PySNMP's incoming transport socket"""
        transport_domain, transport_address = snmp_engine.msgAndPduDsp.getTransportInfo(state_reference)
        sender_address, sender_port = transport_address
        sender_address = ip_address(sender_address)

        router = self._lookup_device(sender_address)
        if not router:
            _logger.info("ignored trap from %s (not a box we monitor?)", sender_address)
            return

        _logger.debug(
            'Trap from %s (%s) ContextEngineId "%s", ContextName "%s"',
            router.name,
            sender_address,
            context_engine_id.prettyPrint(),
            context_name.prettyPrint(),
        )
        origin = TrapOriginator(address=sender_address, port=sender_port, device=router)
        trap = TrapMessage(agent=origin)
        snmp_trap_oid: ObjectName = None
        for var, raw_value in var_binds:
            mib, label, instance, raw_value = self._resolve_varbind(var, raw_value)
            _logger.debug("(%r, %r, %s) = %s", mib, label, instance, raw_value.prettyPrint())
            try:
                value = mib_value_to_python(raw_value)
            except Exception:  # noqa
                value = None
            trap.variables.append(TrapVarBind(OID(var), mib, label, instance, raw_value, value))
            if label == "snmpTrapOID":
                snmp_trap_oid = raw_value

        if not self._verify_trap(trap):
            return

        # TODO do some time calculations, but ask Håvard what the deal is with RestartTime vs. BootTime

        trap.mib, trap.name, _ = self._resolve_object_name(snmp_trap_oid)
        asyncio.ensure_future(self.dispatch_trap(trap))

    @staticmethod
    def _verify_trap(trap: TrapMessage) -> bool:
        device = trap.agent.device.name if trap.agent.device else "N/A"
        if "snmpTrapOID" not in trap:
            _logger.error("Trap from %s did not contain a snmpTrapOID value, ignoring", device)
            return False

        if "sysUpTime" not in trap:
            _logger.error("Trap from %s did not contain a sysUpTime value, ignoring", device)
            return False

        return True

    def _resolve_object_name(self, object_name: ObjectName) -> tuple[str, str, OID]:
        """Raises MibNotFoundError if oid in `object_name` can not be found"""
        engine = self.snmp_engine
        controller = engine.getUserContext("mibViewController")
        if not controller:
            controller = view.MibViewController(engine.getMibBuilder())
        mib, label, instance = controller.getNodeLocation(object_name)
        return mib, label, OID(instance) if instance else None

    def _resolve_varbind(self, name: ObjectName, value: SimpleAsn1Type) -> tuple[str, str, OID, SimpleAsn1Type]:
        """Resolves a varbind name and value to a MIB, label, instance, and value.  The value will be interpreted
        according to the resolved MIB object.

        Raises MibNotFoundError if the object's MIB cannot be resolved.
        """
        engine = self.snmp_engine
        controller = engine.getUserContext("mibViewController")
        if not controller:
            controller = view.MibViewController(engine.getMibBuilder())

        name, value = ObjectType(ObjectIdentity(name), value).resolveWithMib(controller)
        mib, label, instance = name.getMibSymbol()
        return mib, label, instance, value
