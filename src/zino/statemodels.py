"""Basic data models for keeping/serializing/deserializing Zino state"""
import datetime
from enum import Enum, IntEnum
from ipaddress import IPv4Address, IPv6Address
from typing import Dict, List, Optional, Union

from pydantic import BaseModel

IPAddress = Union[IPv4Address, IPv6Address]
PortOrIPAddress = Union[int, IPAddress]


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
    ifdescr: Optional[str]
    ifalias: Optional[str]
    state: Optional[InterfaceOperState]


class Device(BaseModel):
    """Keep device state"""

    name: str
    boot_time: Optional[int]
    ports: Optional[Dict[int, Port]]

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


class LogEntry(BaseModel):
    """Event log entry attributes. These apply both for 'log' and 'history' lists"""

    timestamp: datetime.datetime
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


class EventType(Enum):
    """The set of allowable event types"""

    PORTSTATE = "portstate"
    BGP = "bgp"
    BFD = "bfd"
    REACHABILITY = "reachability"
    ALARM = "alarm"


class Event(BaseModel):
    """Keeps track of event state"""

    id: int

    router: str
    port: Optional[PortOrIPAddress]
    event_type: EventType
    state: EventState
    opened: datetime.datetime
    updated: datetime.datetime
    priority: int

    log: List[LogEntry]
    history: List[LogEntry]

    # More-or-less optional event attrs (as guesstimated from the original Zino code)
    ifindex: Optional[int]
    lasttrans: Optional[datetime.datetime]
    flaps: Optional[int]
    ac_down: Optional[datetime.timedelta]

    polladdr: Optional[IPAddress]
    remote_addr: Optional[IPAddress]
    remote_as: Optional[int]
    peer_uptime: Optional[int]
    alarm_count: Optional[int]

    bfdix: Optional[int]
    bfddiscr: Optional[int]
    bfdaddr: Optional[IPAddress]
