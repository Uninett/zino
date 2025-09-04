import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, NamedTuple, Optional, Set

import zino.state
from zino.config.models import PollDevice
from zino.oid import OID
from zino.statemodels import DeviceState, IPAddress

TrapType = tuple[str, str]  # A mib name and a corresponding trap symbolic name

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
    variables: List[TrapVarBind] = field(default_factory=list)

    def __str__(self):
        variables = [f"{v.mib}::{v.var}{v.instance or ''}={v.value or v.raw_value}" for v in self.variables]
        variables = ", ".join(variables)
        trap_name = f"{self.mib}::{self.name}" if self.mib and self.name else "unknown"
        return f"<Trap from {self.agent.device.name} ({trap_name}): {variables}>"

    def __contains__(self, label) -> bool:
        for var in self.variables:
            if var.var == label:
                return True
        return False

    def get_all(self, label: str) -> List[TrapVarBind]:
        """Returns all contained variables with the given label"""
        return [var for var in self.variables if var.var == label]


class TrapObserver:
    """Defines a valid protocol for SNMP trap observers.

    A trap observer that directly subclasses this protocol can expect to be automatically registered by Zino as an
    observer for any trap it declares in its `WANTED_TRAPS` attribute.
    """

    WANTED_TRAPS: Set[TrapType] = set()

    def __init__(
        self,
        state: zino.state.ZinoState,
        polldevs: Optional[Dict[str, PollDevice]] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ):
        """Initializes a new trap observer with a reference to Zino's state.

        Optionally also receives a reference to the current polldevs configuration and the running event loop.
        """
        self.state = state
        self.polldevs: Dict[str, PollDevice] = polldevs or zino.state.polldevs
        self.loop = loop if loop else asyncio.get_event_loop()

    async def handle_trap(self, trap: TrapMessage) -> Optional[bool]:
        """A trap observer receives a trap message and an optional event loop reference.  The event loop reference
        may be useful if the observer needs to run async actions as part of its trap processing.  If the trap
        observer returns a true-ish value, the trap dispatcher will offer the same trap to more subscribers.  If a
        false-ish value is returned, the trap dispatcher will stop processing this trap.
        """
        ...


class TrapReceiverBase:
    """Base class for Zino SNMP trap receiver back-ends.  Contains common
    functionality for all trap receivers, not specific to any underlying library.
    """

    def __init__(
        self,
        address: str = "0.0.0.0",
        port: int = 162,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        state: Optional[zino.state.ZinoState] = None,
        polldevs: Optional[Dict[str, PollDevice]] = None,
    ):
        self.address = address
        self.port = port
        self.loop = loop if loop else asyncio.get_running_loop()
        self.state = state or zino.state.ZinoState()
        self.polldevs = polldevs if polldevs is not None else {}
        self._communities = set()
        self._observers: dict[TrapType, List[TrapObserver]] = {}
        self._auto_subscribed_observers = set()

    async def open(self):
        """Opens the UDP transport socket and starts receiving traps"""
        raise NotImplementedError

    def close(self):
        """Closes the running SNMP engine and its associated ports"""
        raise NotImplementedError

    def auto_subscribe_observers(self):
        """Automatically subscribes all loaded TrapObserver subclasses to this trap receiver"""
        for observer_class in TrapObserver.__subclasses__():
            if not observer_class.WANTED_TRAPS:
                continue
            if observer_class in self._auto_subscribed_observers:
                continue
            else:
                self._auto_subscribed_observers.add(observer_class)
            observer_instance = observer_class(state=self.state, polldevs=self.polldevs, loop=self.loop)
            self.observe(observer_instance, *observer_instance.WANTED_TRAPS)

    def observe(self, subscriber: TrapObserver, *trap_types: List[TrapType]):
        """Adds a trap subscriber to the receiver"""
        for trap_type in trap_types:
            observers = self._observers.setdefault(trap_type, [])
            observers.append(subscriber)

    def get_observers_for(self, trap_type: TrapType) -> List[TrapObserver]:
        """Returns a list of trap observers for a given trap type"""
        return self._observers.get(trap_type, [])

    def add_community(self, community: str):
        """Adds a new community string that will be accepted on incoming packets"""
        if community in self._communities:
            return
        self._communities.add(community)

    async def dispatch_trap(self, trap: TrapMessage):
        """Dispatches incoming trap messages according to internal subscriptions"""
        observers = self.get_observers_for((trap.mib, trap.name))
        if not observers:
            _logger.debug("unknown trap: %s", trap)
            return

        for observer in observers:
            try:
                if not await observer.handle_trap(trap):
                    return
            except Exception:  # noqa
                _logger.exception("Unhandled exception in trap observer %r", observer)

    def _lookup_device(self, address: IPAddress) -> Optional[DeviceState]:
        """Looks up a device from Zino's running state from an IP address"""
        name = self.state.addresses.get(address)
        if name in self.state.devices:
            return self.state.devices[name]
