"""SNMP trap 'daemon' for Zino 2"""
import asyncio
import logging
from dataclasses import dataclass, field
from ipaddress import ip_address
from typing import Any, List, NamedTuple, Optional, Protocol, Set

from pysnmp.carrier.asyncio.dgram import udp
from pysnmp.entity import config
from pysnmp.entity.rfc3413 import ntfrcv
from pysnmp.proto.rfc1902 import ObjectName
from pysnmp.smi import view

from zino.oid import OID
from zino.snmp import _mib_value_to_python, get_new_snmp_engine
from zino.state import ZinoState
from zino.statemodels import DeviceState, IPAddress

TrapType = tuple[str, str]  # A mib name and a corresponding trap symbolic name
# These are spammy traps observed in Uninett, and we don't care about them:
IGNORED_TRAPS: Set[TrapType] = {
    ("BGP4-MIB", "bgpBackwardTransition"),
    ("BGP4-MIB", "bgpBackwardTransNotification"),
    ("BGP4-V2-MIB-JUNIPER", "jnxBgpM2BackwardTransition"),
    ("SNMPv2-MIB", "authenticationFailure"),
    ("CISCOTRAP-MIB", "tcpConnectionClose"),
    ("BGP4-V2-MIB-JUNIPER", "jnxBgpM2BackwardTransition"),
}
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


class TrapObserver(Protocol):
    """Defines a valid protocol for SNMP trap observers.

    A trap observer that directly subclasses this protocol can expect to be automatically registered by Zino as an
    observer for any trap it declares in its `WANTED_TRAPS` attribute.
    """

    WANTED_TRAPS: Set[TrapType] = set()

    def __init__(self, state: ZinoState, loop: Optional[asyncio.AbstractEventLoop] = None):
        self.state = state
        self.loop = loop if loop else asyncio.get_event_loop()

    def handle_trap(self, trap: TrapMessage) -> Optional[bool]:
        """A trap observer receives a trap message and an optional event loop reference.  The event loop reference
        may be useful if the observer needs to run async actions as part of its trap processing.  If the trap
        observer returns a true-ish value, the trap dispatcher will offer the same trap to more subscribers.  If a
        false-ish value is returned, the trap dispatcher will stop processing this trap.
        """
        ...


class TrapReceiver:
    """Zino Adapter for SNMP trap reception using PySNMP.

    A major difference to Zino 1 is that this receiver must explicitly be configured with SNMP community strings that
    will be accepted.  Zino 1 accepts traps with any community string, as long as their origin is any one of the
    devices configured in `polldevs.cf`.  However, PySNMP places heavy emphasis on being standards compliant,
    and will not even pass on traps to our callbacks unless they match the authorization config for the SNMP engine.
    """

    def __init__(
        self,
        address: str = "0.0.0.0",
        port: int = 162,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        state: Optional[ZinoState] = None,
    ):
        self.transport: udp.UdpTransport = None
        self.address = address
        self.port = port
        self.loop = loop if loop else asyncio.get_event_loop()
        self.state = state or ZinoState()
        self.snmp_engine = get_new_snmp_engine()
        self._communities = set()
        self._observers: dict[TrapType, List[TrapObserver]] = {}

        self.observe(ignore_trap, *IGNORED_TRAPS)

    def observe(self, subscriber: TrapObserver, *trap_types: List[TrapType]):
        """Adds a trap subscriber to the receiver"""
        for trap_type in trap_types:
            observers = self._observers.setdefault(trap_type, [])
            observers.append(subscriber)

    def get_observers_for(self, trap_type: TrapType) -> List[TrapObserver]:
        """Returns a list of trap observers for a given trap type"""
        return self._observers.get(trap_type, [])

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

        _logger.debug(
            'Trap from %s (%s) ContextEngineId "%s", ContextName "%s"',
            router.name,
            sender_address,
            context_engine_id.prettyPrint(),
            context_name.prettyPrint(),
        )
        origin = TrapOriginator(address=sender_address, port=sender_port, device=router)
        trap = TrapMessage(agent=origin)
        for var, raw_value in var_binds:
            mib, label, instance = self._resolve_object_name(var)
            _logger.debug("(%r, %r, %s) = %s", mib, label, instance, raw_value.prettyPrint())
            try:
                value = _mib_value_to_python(raw_value)
            except Exception:  # noqa
                value = None
            trap.variables[label] = TrapVarBind(OID(var), mib, label, instance, raw_value, value)

        if not self._verify_trap(trap):
            return

        # TODO do some time calculations, but ask Håvard what the deal is with RestartTime vs. BootTime

        trap.mib, trap.name, _ = self._resolve_object_name(trap.variables["snmpTrapOID"].raw_value)
        self.dispatch_trap(trap)

    @staticmethod
    def _verify_trap(trap: TrapMessage) -> bool:
        device = trap.agent.device.name if trap.agent.device else "N/A"
        if "snmpTrapOID" not in trap.variables:
            _logger.error("Trap from %s did not contain a snmpTrapOID value, ignoring", device)
            return False

        if "sysUpTime" not in trap.variables:
            _logger.error("Trap from %s did not contain a sysUpTime value, ignoring", device)
            return False

        return True

    def dispatch_trap(self, trap: TrapMessage):
        """Dispatches incoming trap messages according to internal subscriptions"""
        observers = self.get_observers_for((trap.mib, trap.name))
        if not observers:
            _logger.info("unknown trap: %s", trap)
            return

        for observer in observers:
            try:
                if not observer.handle_trap(trap):
                    return
            except Exception:  # noqa
                _logger.exception("Unhandled exception in trap observer %r", observer)

    def _lookup_device(self, address: IPAddress) -> Optional[DeviceState]:
        """Looks up a device from Zino's running state from an IP address"""
        name = self.state.addresses.get(address)
        if name in self.state.devices:
            return self.state.devices[name]

    def _resolve_object_name(self, object_name: ObjectName) -> tuple[str, str, OID]:
        """Raises MibNotFoundError if oid in `object_name` can not be found"""
        engine = self.snmp_engine
        controller = engine.getUserContext("mibViewController")
        if not controller:
            controller = view.MibViewController(engine.getMibBuilder())
        mib, label, instance = controller.getNodeLocation(object_name)
        return mib, label, OID(instance) if instance else None


def ignore_trap(trap: TrapMessage, loop: Optional[asyncio.AbstractEventLoop] = None) -> Optional[bool]:
    """Trap observer that just ignores incoming traps"""
    return False
