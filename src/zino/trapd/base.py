import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, NamedTuple, Optional, Set

import zino.state
from zino.config.models import PollDevice
from zino.oid import OID
from zino.statemodels import DeviceState, IPAddress

TrapType = tuple[str, str]  # A mib name and a corresponding trap symbolic name


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
        return f"<Trap from {self.agent.device.name}: {variables}>"

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
