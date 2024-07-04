import logging
from datetime import datetime, timedelta
from typing import get_args

from zino.events import EventIndex
from zino.state import ZinoState
from zino.stateconverter.linedata import LineData
from zino.stateconverter.utils import OldState, parse_ip, parse_log_and_history
from zino.statemodels import (
    AlarmEvent,
    AlarmType,
    BFDEvent,
    BFDSessState,
    BGPAdminStatus,
    BGPEvent,
    BGPOperState,
    EventState,
    InterfaceState,
    PortStateEvent,
    ReachabilityEvent,
    ReachabilityState,
    SubIndex,
)

_log = logging.getLogger(__name__)


event_name_to_type = {
    "bgp": BGPEvent,
    "bfd": BFDEvent,
    "reachability": ReachabilityEvent,
    "alarm": AlarmEvent,
    "portstate": PortStateEvent,
}


EventIndices = dict[str, EventIndex]


def set_event_state(
    old_state: OldState,
    new_state: ZinoState,
):
    event_indices: EventIndices = {}
    for linedata in old_state["::EventIdToIx"]:
        event_id, event_index = _get_event_index(linedata)
        event_indices[event_id] = event_index
    for linedata in old_state["::EventAttrs"]:
        try:
            _set_event_attrs(linedata, new_state, event_indices)
        except ValueError as e:
            _log.error(f"Error setting event attribute: {str(e)}")
    new_state.events._rebuild_indexes()


def _get_event_index(line: LineData) -> tuple[int, EventIndex]:
    """Parses a LineData representing an EventIdToIx line and returns a tuple
    of event_id, event_index
    """
    event_id = int(line.identifiers[0])

    index_components = line.value.split(",")
    if len(index_components) not in [2, 3]:
        raise ValueError(f"Invalid event index {line.value}")
    device, *rest = index_components
    # The last component should always be the event type
    event_type = rest.pop() if rest else None
    # If anything is left, it should be the subindex
    subindex = _parse_subindex(rest[0]) if rest else None

    event_index = EventIndex(device, subindex, event_name_to_type[event_type])
    return event_id, event_index


def _parse_subindex(subindex: str) -> SubIndex:
    """Parses the part of a EventIdToIx line that defines the ip/port value"""
    if subindex is None:
        return subindex
    if subindex in get_args(AlarmType):
        return subindex
    try:
        return parse_ip(subindex)
    except ValueError:
        pass
    try:
        return int(subindex)
    except ValueError:
        pass
    raise ValueError(f"Invalid SubIndex: {subindex}")


def _set_event_attrs(linedata: LineData, state: ZinoState, indices: EventIndices):
    event_field = linedata.identifiers[0]
    event_id = int(linedata.identifiers[1])
    event_index = indices[event_id]
    state.events.last_event_id = max(state.events.last_event_id, event_id)
    if event_id in state.events.events:
        event = state.events.events[event_id]
    else:
        event = state.events.create_event(*event_index)
        event.id = event_id
    if event_field == "priority":
        event.priority = int(linedata.value)
    elif event_field == "history":
        event.history = parse_log_and_history(linedata.value)
    elif event_field == "bgpOS":
        event.bgpos = BGPOperState(linedata.value)
    elif event_field == "bgpAS":
        event.bgpas = BGPAdminStatus(linedata.value)
    elif event_field == "lastevent":
        event.lastevent = linedata.value
    elif event_field == "log":
        event.log = parse_log_and_history(linedata.value)
    elif event_field == "polladdr":
        event.polladdr = parse_ip(linedata.value)
    elif event_field == "opened":
        event.opened = datetime.fromtimestamp(int(linedata.value))
    elif event_field == "peer-uptime":
        event.peer_uptime = int(linedata.value)
    elif event_field == "remote-AS":
        event.remote_as = int(linedata.value)
    elif event_field == "remote-addr":
        event.remote_addr = parse_ip(linedata.value)
    elif event_field == "router":
        event.router = linedata.value
    elif event_field == "state":
        event.state = EventState(linedata.value)
    elif event_field == "updated":
        event.updated = datetime.fromtimestamp(int(linedata.value))
    elif event_field == "ac-down":
        event.ac_down = timedelta(seconds=int(linedata.value))
    elif event_field == "descr":
        event.descr = linedata.value
    elif event_field == "flaps":
        _log.info("flaps is not a supported event field")
    elif event_field == "flapstate":
        _log.info("flapstate is not a supported event field")
    elif event_field == "ifindex":
        event.ifindex = int(linedata.value)
    elif event_field == "portstate":
        event.portstate = InterfaceState(linedata.value)
    elif event_field == "port":
        event.port = linedata.value
    elif event_field == "bfdAddr":
        if "unknown" in linedata.value:
            pass
        else:
            event.bfdaddr = parse_ip(linedata.value)
    elif event_field == "bfdDiscr":
        event.bfddiscr = int(linedata.value)
    elif event_field == "bfdIx":
        event.bfdix = int(linedata.value)
    elif event_field == "bfdState":
        event.bfdstate = BFDSessState(linedata.value)
    elif event_field == "lasttrans":
        event.lasttrans = datetime.fromtimestamp(int(linedata.value))
    elif event_field == "alarm-count":
        event.alarm_count = int(linedata.value)
    elif event_field == "alarm-type":
        event.alarm_type = linedata.value
    elif event_field == "Neigh-rDNS":
        event.neigh_rdns = linedata.value
    elif event_field == "reachability":
        event.reachability = ReachabilityState(linedata.value)
    elif event_field == "reason":
        event.reason = linedata.value
    elif event_field in ["id", "type"]:
        # These are set via other means
        pass
    else:
        raise ValueError(f"Unknown event attribute {event_field}")
    state.events.events[event.id] = event
