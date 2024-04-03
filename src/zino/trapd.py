"""SNMP trap 'daemon' for Zino 2"""
import asyncio
import logging
from dataclasses import dataclass, field
from ipaddress import ip_address
from typing import Any, NamedTuple, Optional

from pysnmp.carrier.asyncio.dgram import udp
from pysnmp.entity import config
from pysnmp.entity.rfc3413 import ntfrcv

from zino.oid import OID
from zino.snmp import _get_engine
from zino.state import ZinoState
from zino.statemodels import DeviceState, IPAddress

_logger = logging.getLogger(__name__)


class TrapVarBind(NamedTuple):
    """Describes a single trap varbind as high-level as possible, but with low level details available as well"""

    oid: OID
    mib: str
    var: str
    instance: OID
    raw_value: Any
    value: Any


class TrapOriginator(NamedTuple):
    """Describes the originating SNMP agent of a trap message in Zino terms"""

    address: IPAddress
    port: int
    device: Optional[DeviceState] = None


@dataclass
class TrapMessage:
    """Describes an incoming trap message in the simplest possible terms needed for Zino usage"""

    agent: TrapOriginator
    mib: Optional[str] = None
    name: Optional[str] = None
    variables: dict[str, TrapVarBind] = field(default_factory=dict)

    def __str__(self):
        variables = [f"{v.mib}::{v.var}{v.instance or ''}={v.value or v.raw_value}" for v in self.variables.values()]
        variables = ", ".join(variables)
        return f"<Trap from {self.agent.device.name}: {variables}>"


class TrapReceiver:
    """Zino Adapter for SNMP trap reception using PySNMP.

    A major difference to Zino 1 is that this receiver must explicitly be configured with SNMP community strings that
    will be accepted.  Zino 1 accepts traps with any community string, as long as their origin is any one of the
    devices configured in `polldevs.cf`.  However, PySNMP places heavy emphasis on being standards compliant,
    and will not even pass on traps to our callbacks unless they match the authorization config for the SNMP engine.
    """

    def __init__(self, address: str = "0.0.0.0", port: int = 162, loop=None, state: Optional[ZinoState] = None):
        self.transport: udp.UdpTransport = None
        self.address = address
        self.port = port
        self.loop = loop if loop else asyncio.get_event_loop()
        self.state = state or ZinoState()
        self.snmp_engine = _get_engine()
        self._communities = set()

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
        if community in self._communities:
            return
        self._communities.add(community)
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

        _logger.info(
            'Trap from %s (%s) ContextEngineId "%s", ContextName "%s"',
            router.name,
            sender_address,
            context_engine_id.prettyPrint(),
            context_name.prettyPrint(),
        )
        for name, val in var_binds:
            _logger.info("%s = %s", name.prettyPrint(), val.prettyPrint())

    def _lookup_device(self, address: IPAddress) -> Optional[DeviceState]:
        """Looks up a device from Zino's running state from an IP address"""
        name = self.state.addresses.get(address)
        if name in self.state.devices:
            return self.state.devices[name]
