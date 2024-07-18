"""Basic data models for keeping/serializing/deserializing Zino state"""

import datetime
import fnmatch
import logging
import pathlib
import re
from collections.abc import Generator
from enum import Enum
from ipaddress import IPv4Address, IPv6Address
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterator,
    List,
    Literal,
    Optional,
    Sequence,
    TypeVar,
    Union,
)

from pydantic import BaseModel, Field

from zino.compat import StrEnum
from zino.time import now

if TYPE_CHECKING:
    from zino.state import ZinoState

IPAddress = Union[IPv4Address, IPv6Address]
AlarmType = Literal["yellow", "red"]
SubIndex = Union[None, int, IPAddress, AlarmType]
EventType = TypeVar("EventType", bound="Event")
CISCO_ENTERPRISE_ID = 9
JUNIPER_ENTERPRISE_ID = 2636

_logger = logging.getLogger(__name__)


class ClosedEventError(Exception):
    """Closed events cannot be reopened"""

    pass


class BGPStyle(StrEnum):
    """The set of allowable BGP styles"""

    JUNIPER = "juniper"
    CISCO = "cisco"
    GENERAL = "general"


class BGPAdminStatus(StrEnum):
    """The set of allowable BGP admin status"""

    RUNNING = "running"
    HALTED = "halted"
    START = "start"
    STOP = "stop"


class BGPOperState(StrEnum):
    """The set of allowable BGP oper states"""

    IDLE = "idle"
    CONNECT = "connect"
    ACTIVE = "active"
    OPENSENT = "opensent"
    OPENCONFIRM = "openconfirm"
    ESTABLISHED = "established"
    DOWN = "down"


class InterfaceState(StrEnum):
    """Enumerates allowable interface states.  Most of these values come from ifOperState from RFC 2863 (IF-MIB), but
    also adds internal Zino states that don't exist in the MIB.
    """

    ADMIN_DOWN = "adminDown"
    UP = "up"
    DOWN = "down"
    TESTING = "testing"
    UNKNOWN = "unknown"
    DORMANT = "dormant"
    NOT_PRESENT = "notPresent"
    LOWER_LAYER_DOWN = "lowerLayerDown"
    FLAPPING = "flapping"  # Zino-specific


class BFDSessState(StrEnum):
    """The set of allowable BFD session states"""

    ADMIN_DOWN = "adminDown"
    DOWN = "down"
    INIT = "init"
    UP = "up"
    FAILING = "failing"  # Cisco proprietary


class BFDState(BaseModel):
    """Keeps BFD state for an interface"""

    session_state: BFDSessState
    session_index: Optional[int] = None
    session_discr: Optional[int] = None
    session_addr: Optional[IPAddress] = None


class Port(BaseModel):
    """Keeps port state"""

    ifindex: int
    ifdescr: Optional[str] = None
    ifalias: Optional[str] = None
    state: Optional[InterfaceState] = None
    bfd_state: Optional[BFDState] = None


class BGPPeerSession(BaseModel):
    """Keeps a BGP peer session"""

    uptime: Optional[int] = 0
    admin_status: Optional[BGPAdminStatus] = None
    oper_state: Optional[BGPOperState] = None


class DeviceState(BaseModel):
    """Keep device state"""

    name: str
    addresses: set[IPAddress] = set()
    enterprise_id: Optional[int] = None
    ports: Dict[int, Port] = {}
    alarms: Optional[Dict[AlarmType, int]] = None
    boot_time: Optional[datetime.datetime] = None
    bgp_style: Optional[BGPStyle] = None
    bgp_peers: dict[IPAddress, BGPPeerSession] = dict()

    # This is the remaining set of potential device attributes stored in device state by the original Zino code:
    # EventId
    # JNXalarms
    # RunsOn
    # bfdSessAddr
    # bfdSessAddrType
    # bfdSessDiscr
    # bfdSessState
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
        return self.enterprise_id == CISCO_ENTERPRISE_ID

    @property
    def is_juniper(self):
        return self.enterprise_id == JUNIPER_ENTERPRISE_ID

    def set_boot_time_from_uptime(self, uptime: int):
        """Calculates and sets the device boot time from a current uptime value.

        :param uptime: An uptime value in 100ths of a second
        """
        self.boot_time = now() - datetime.timedelta(seconds=uptime / 100)


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

    def model_dump_legacy(self) -> List[str]:
        """Returns the contents of this log entry as a sequence of text lines.

        This sequence of text lines are formatted as expected in a multi-line response in the Zino legacy server
        protocol:

        The first line starts with a UNIX integer timestamp, followed by a space and then the first line of the entry
        text.  Each subsequent line of the entry text is prefixed by a space, which in the protocol signifies a
        continuation line.

        Example:
        >>> LogEntry(message="This is a\\nmulti-line entry").model_dump_legacy()
        ['1701171730 This is a', ' multiline entry']
        >>>
        """
        unix_timestamp = int(self.timestamp.timestamp())
        lines = [f" {line}" for line in self.message.splitlines()]
        lines[0] = f"{unix_timestamp}{lines[0]}"
        return lines


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

    id: Optional[int] = None

    router: str
    type: Literal["Event"] = "Event"
    state: EventState = EventState.EMBRYONIC
    opened: datetime.datetime = Field(default_factory=now)
    updated: Optional[datetime.datetime] = None
    priority: int = 100
    lastevent: Optional[str] = None

    log: List[LogEntry] = []
    history: List[LogEntry] = []

    # More-or-less optional event attrs (as guesstimated from the original Zino code)
    lasttrans: Optional[datetime.datetime] = None
    flaps: Optional[int] = None
    ac_down: Optional[datetime.timedelta] = None

    polladdr: Optional[IPAddress] = None

    @property
    def subindex(self) -> SubIndex:
        """Returns an identifier of a router subcomponent that this event refers to.

        This value is used to index an event uniquely, and the property itself is usually only called if the event index
        class needs to re-index all existing events - something that usually only happens when loading serialized
        state from disk.
        """
        return None

    def set_state(self, new_state: EventState, user: str = "monitor"):
        """Sets a new event state value, logging the change to the event history with a username"""
        if new_state == self.state:
            return
        if self.state == EventState.CLOSED:
            raise ClosedEventError

        old_state, self.state = self.state, new_state
        if (old_state, new_state) == (EventState.EMBRYONIC, EventState.OPEN):
            self.opened = now()
        self.add_history(f"state change {old_state.value} -> {new_state.value} ({user})")
        _logger.debug("id %s state %s -> %s by %s", self.id, old_state.value, new_state.value, user)

    def add_log(self, message: str) -> LogEntry:
        entry = LogEntry(message=message)
        self.log.append(entry)
        self.updated = entry.timestamp
        return entry

    def add_history(self, message: str) -> LogEntry:
        entry = LogEntry(message=message)
        self.history.append(entry)
        return entry

    def model_dump_simple_attrs(self) -> dict[str, str]:
        """Serializes the "simple" attributes of this event to the text format used by the legacy Zino protocol.

        "Simple" attributes are typically "single line" public attributes, i.e. anything but `log` or `history`.

        It would be nice to be able to attach custom serializers to fields, but we need to support multiple
        serialization formats (one for JSON state dumps, one for the legacy Zino protocol), and it's not clear how
        Pydantic can support that.
        """
        attrs = self.model_dump(mode="python", exclude={"log", "history"}, exclude_none=True)
        return {attr.replace("_", "-"): self.zinoify_value(value) for attr, value in attrs.items()}

    @staticmethod
    def zinoify_value(value: Any) -> str:
        """Serializes an Event value into a plain string in the format expected by the legacy Zino protocol"""
        if isinstance(value, Enum):
            return str(value.value)
        if isinstance(value, datetime.datetime):
            return str(int(value.timestamp()))
        if isinstance(value, datetime.timedelta):
            return str(int(value.total_seconds()))
        return str(value)

    def get_changed_fields(self, other: "Event") -> List[str]:
        """Compares this Event to another Event and returns a list of names of attributes that are different"""
        return [field for field in self.model_fields if getattr(other, field) != getattr(self, field)]

    def dump_event_to_file(self, dir_name: str):
        """Dumps the full event to a file in JSON format"""
        pathlib.Path(dir_name).mkdir(parents=True, exist_ok=True)
        filename = f"{dir_name}/{self.id}.json"
        _logger.debug("dumping state to %s", filename)
        with open(filename, "w") as statefile:
            statefile.write(self.model_dump_json(exclude_none=True, indent=2))


class FlapState(StrEnum):
    FLAPPING = "flapping"
    STABLE = "stable"


class PortStateEvent(Event):
    type: Literal["portstate"] = "portstate"
    port: Optional[str] = ""
    ifindex: Optional[int] = None
    portstate: Optional[InterfaceState] = None
    descr: Optional[str] = None
    flapstate: Optional[FlapState] = None
    reason: Optional[str] = None

    @property
    def subindex(self) -> SubIndex:
        return self.ifindex


class BGPEvent(Event):
    type: Literal["bgp"] = "bgp"
    remote_addr: Optional[IPAddress] = None
    remote_as: Optional[int] = None
    peer_uptime: Optional[int] = None
    bgpos: Optional[BGPOperState] = None
    bgpas: Optional[BGPAdminStatus] = None

    @property
    def subindex(self) -> SubIndex:
        return self.remote_addr


class BFDEvent(Event):
    type: Literal["bfd"] = "bfd"
    ifindex: Optional[int] = None
    bfdstate: Optional[BFDSessState] = None
    bfdix: Optional[int] = None
    bfddiscr: Optional[int] = None
    bfdaddr: Optional[IPAddress] = None
    neigh_rdns: Optional[str] = None

    @property
    def subindex(self) -> SubIndex:
        return self.ifindex


class ReachabilityEvent(Event):
    type: Literal["reachability"] = "reachability"
    reachability: Optional[ReachabilityState] = None


class AlarmEvent(Event):
    type: Literal["alarm"] = "alarm"
    alarm_type: Optional[AlarmType] = None
    alarm_count: Optional[int] = None

    @property
    def subindex(self) -> SubIndex:
        return self.alarm_type


class MatchType(StrEnum):
    """The set of allowable match types for PlannedMaintenanc objects"""

    REGEXP = "regexp"
    STR = "str"
    EXACT = "exact"
    INTF_REGEXP = "intf-regexp"


class PmType(StrEnum):
    """The set of allowable types for PlannedMaintenance objects"""

    PORTSTATE = "portstate"
    DEVICE = "device"


class PlannedMaintenance(BaseModel):
    id: Optional[int] = None
    start_time: datetime.datetime
    end_time: datetime.datetime
    type: PmType
    match_type: MatchType
    match_device: Optional[str] = None
    match_expression: str
    log: List[LogEntry] = []
    event_ids: List[int] = []

    def start(self, state: "ZinoState"):
        events = self._get_or_create_events(state)
        for event in events:
            # get special handling of embryonic -> open transition first
            state.events.commit(event)
            event.state = EventState.IGNORED
            state.events.commit(event)
            self.event_ids.append(event.id)

    def end(self, state: "ZinoState"):
        for event_id in self.event_ids:
            event = state.events.checkout(event_id)
            event.state = EventState.OPEN
            state.events.commit(event)

    def add_log(self, message: str) -> LogEntry:
        entry = LogEntry(message=message)
        self.log.append(entry)
        return entry

    def details(self) -> str:
        """Returns a string with the details of the object.
        Format from zino1: $id $from_t $to_t $type $match_type [$match_dev] $match_expr
        """
        details = [
            str(int(attr.timestamp())) if isinstance(attr, datetime.datetime) else str(attr)
            for attr in [
                self.id,
                self.start_time,
                self.end_time,
                self.type,
                self.match_type,
                self.match_device,
                self.match_expression,
            ]
            if attr
        ]
        return " ".join(details)

    def matches_event(self, event: Event, state: "ZinoState") -> bool:
        """Returns true if `event` will be affected by this planned maintenance"""
        raise NotImplementedError

    def _get_or_create_events(self, state: "ZinoState") -> list[Event]:
        """Creates/gets events that are affected by the given starting planned
        maintenance
        """
        raise NotImplementedError

    def get_matching(self, state: "ZinoState") -> Iterator[Sequence[Union[str, int]]]:
        """Returns a list of matching devices or ports from Zino state.

        The number of elements of each sequence of the return value depends on the type of planned maintenance
        objects, but each entry should be suitable to join on space and output to the legacy API.
        """
        raise NotImplementedError


class DeviceMaintenance(PlannedMaintenance):
    type: Literal[PmType.DEVICE] = PmType.DEVICE

    def matches_event(self, event: Event, state: "ZinoState") -> bool:
        """Returns true if `event` will be affected by this planned maintenance"""
        if not isinstance(event, (ReachabilityEvent, AlarmEvent)):
            return False
        device = state.devices[event.router]
        return self.matches_device(device)

    def matches_device(self, device: DeviceState) -> bool:
        """Returns true if ReachabilityEvents and AlarmEvents related to `device`
        would be affected by this planned maintenance
        """
        if self.match_type == "regexp":
            return regex_match(self.match_expression, device.name)
        if self.match_type == "str":
            return string_match(self.match_expression, device.name)
        if self.match_type == "exact":
            return self.match_expression == device.name
        return False

    def get_matching(self, state: "ZinoState") -> Iterator[Sequence[Union[str, int]]]:
        """Returns a list of matching devices from Zino state.

        Each element is a sequence of (pm_id, "device", device_name)
        """
        for device in state.devices.devices.values():
            if self.matches_device(device):
                yield self.id, self.type, device.name

    def _get_or_create_events(self, state: "ZinoState") -> list[Event]:
        """Creates/gets events that are affected by the given starting planned
        maintenance
        """
        events = []
        # all devices that the pm should affect
        devices = (device for device in state.devices.devices.values() if self.matches_device(device))
        for device in devices:
            reachability_event = state.events.get_or_create_event(device.name, None, ReachabilityEvent)
            yellow_event = state.events.get_or_create_event(device.name, "yellow", AlarmEvent)
            yellow_event.alarm_type = "yellow"
            red_event = state.events.get_or_create_event(device.name, "red", AlarmEvent)
            red_event.alarm_type = "red"
            for event in (reachability_event, yellow_event, red_event):
                events.append(event)
        return events


class PortStateMaintenance(PlannedMaintenance):
    type: Literal[PmType.PORTSTATE] = PmType.PORTSTATE

    def matches_event(self, event: Event, state: "ZinoState") -> bool:
        """Returns true if `event` will be affected by this planned maintenance"""
        if event.type != "portstate":
            return False
        device = state.devices[event.router]
        port = device.ports[event.ifindex]
        return self.matches_portstate(device, port)

    def matches_portstate(self, device: DeviceState, port: Port) -> bool:
        """Returns true if PortstateEvents related to `port` on `device`
        would be affected by this planned maintenance
        """
        if self.match_type == "regexp":
            return regex_match(self.match_expression, port.ifdescr)
        if self.match_type == "str":
            return string_match(self.match_expression, port.ifdescr)
        if self.match_type == "intf-regexp":
            if regex_match(self.match_device, device.name):
                return regex_match(self.match_expression, port.ifdescr)
        return False

    def get_matching(self, state: "ZinoState") -> Iterator[Sequence[Union[str, int]]]:
        """Returns a list of matching devices from Zino state.

        Each element is a sequence of (pm_id, "portstate", device_name, ifIndex, ifDescr, f"({ifAlias})")
        """
        for device in state.devices.devices.values():
            for port in device.ports.values():
                if self.matches_portstate(device, port):
                    yield self.id, self.type, device.name, port.ifindex, port.ifdescr, f"({port.ifalias})"

    def _get_or_create_events(self, state: "ZinoState") -> list[Event]:
        events = []
        for device, port in self._get_matching_ports(state):
            event = state.events.get_or_create_event(device.name, port.ifindex, PortStateEvent)
            event.ifindex = port.ifindex
            events.append(event)
        return events

    def _get_matching_ports(self, state: "ZinoState") -> Generator[tuple[DeviceState, Port], None, None]:
        for device in state.devices.devices.values():
            for port in device.ports.values():
                if self.matches_portstate(device, port):
                    yield (device, port)


def string_match(pattern: str, string: str) -> bool:
    """This should behave like tcl string match https://wiki.tcl-lang.org/page/string+match
    Returns true if `string` matches `pattern`.
    """
    return fnmatch.fnmatch(string, pattern)


def regex_match(pattern: str, string: str) -> bool:
    """Matches `string` against regex expression `pattern`.
    Returns true if there is a match.
    """
    return bool(re.match(pattern, string))
