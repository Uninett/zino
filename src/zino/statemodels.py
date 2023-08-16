"""Basic data models for keeping/serializing/deserializing Zino state"""
import datetime
from enum import Enum, IntEnum
from ipaddress import IPv4Address, IPv6Address
from typing import Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field

from zino.time import now

IPAddress = Union[IPv4Address, IPv6Address]
AlarmType = Literal["yellow", "red"]
PortOrIPAddress = Union[int, IPAddress, AlarmType]


class InterfaceOperState(IntEnum):
    """Enumerates ifOperState from RFC 2863 (IF-MIB)"""

    up = 1
    down = 2
    testing = 3
    unknown = 4
    dormant = 5
    notPresent = 6
    lowerLayerDown = 7


class Port(BaseModel):
    """Keeps port state"""

    ifindex: int
    ifdescr: Optional[str] = None
    ifalias: Optional[str] = None
    state: Optional[InterfaceOperState] = None


class DeviceState(BaseModel):
    """Keep device state"""

    name: str
    enterprise_id: Optional[int] = None
    boot_time: Optional[int] = None
    ports: Dict[int, Port] = {}
    alarms: Optional[Dict[AlarmType, int]] = None

    # This is the remaining set of potential device attributes stored in device state by the original Zino code:
    # BootTime
    # EventId
    # JNXalarms
    # RunsOn
    # bfdSessAddr
    # bfdSessAddrType
    # bfdSessDiscr
    # bfdSessState
    # bgpPeerAdminState
    # bgpPeerOperState
    # bgpPeerUpTime
    # bgpPeers
    # firstFlap
    # flapping
    # flaps
    # isCisco
    # isJuniper
    # lastAge
    # lastFlap
    # portState
    # portToIfDescr
    # portToLocIfDescr
    # sawPeer

    @property
    def is_cisco(self):
        return self.enterprise_id == 9

    @property
    def is_juniper(self):
        return self.enterprise_id == 2636


class DeviceStates(BaseModel):
    """Keeps track of the state of all devices we have polled from"""

    devices: Dict[str, DeviceState] = {}

    def __getitem__(self, item) -> DeviceState:
        return self.devices[item]

    def __contains__(self, item):
        return item in self.devices

    def __len__(self):
        return len(self.devices)

    def get(self, device_name: str) -> DeviceState:
        """Returns a DeviceState object for device_name, creating a blank state object if none exists"""
        if device_name not in self:
            self.devices[device_name] = DeviceState(name=device_name)
        return self[device_name]


class LogEntry(BaseModel):
    """Event log entry attributes. These apply both for 'log' and 'history' lists"""

    timestamp: datetime.datetime = Field(default_factory=now)
    message: str


class EventState(Enum):
    """The set of allowable event states"""

    EMBRYONIC = "embryonic"
    OPEN = "open"
    WORKING = "working"
    WAITING = "waiting"
    CONFIRM = "confirm-wait"
    IGNORED = "ignored"
    CLOSED = "closed"


class ReachabilityState(Enum):
    """The set of allowed reachability states"""

    REACHABLE = "reachable"
    NORESPONSE = "no-response"


class Event(BaseModel):
    """Keeps track of event state"""

    id: int

    router: str
    port: Optional[PortOrIPAddress] = None
    type: Literal["Event"] = "Event"
    state: EventState
    opened: datetime.datetime = Field(default_factory=now)
    updated: Optional[datetime.datetime] = None
    priority: int = 100

    log: List[LogEntry] = []
    history: List[LogEntry] = []

    # More-or-less optional event attrs (as guesstimated from the original Zino code)
    lasttrans: Optional[datetime.datetime] = None
    flaps: Optional[int] = None
    ac_down: Optional[datetime.timedelta] = None

    polladdr: Optional[IPAddress] = None

    def add_log(self, message: str) -> LogEntry:
        entry = LogEntry(message=message)
        self.log.append(entry)
        self.updated = entry.timestamp
        return entry

    def add_history(self, message: str) -> LogEntry:
        entry = LogEntry(message=message)
        self.history.append(entry)
        return entry


class PortStateEvent(Event):
    type: Literal["portstate"] = "portstate"
    ifindex: Optional[int] = None


class BGPEvent(Event):
    type: Literal["bgp"] = "bgp"
    remote_addr: Optional[IPAddress] = None
    remote_as: Optional[int] = None
    peer_uptime: Optional[int] = None


class BFDEvent(Event):
    type: Literal["bfd"] = "bfd"
    bfdix: Optional[int] = None
    bfddiscr: Optional[int] = None
    bfdaddr: Optional[IPAddress] = None


class ReachabilityEvent(Event):
    type: Literal["reachability"] = "reachability"
    reachability: Optional[ReachabilityState] = None


class AlarmEvent(Event):
    type: Literal["alarm"] = "alarm"
    alarm_count: Optional[int] = None
