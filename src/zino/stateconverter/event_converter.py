import logging
from datetime import datetime, timedelta, timezone

from zino.state import ZinoState
from zino.stateconverter.linedata import LineData
from zino.stateconverter.utils import OldState, parse_ip, parse_log_and_history
from zino.statemodels import (
    AlarmEvent,
    BFDEvent,
    BFDSessState,
    BGPAdminStatus,
    BGPEvent,
    BGPOperState,
    EventState,
    FlapState,
    InterfaceState,
    PortStateEvent,
    ReachabilityEvent,
    ReachabilityState,
)

_log = logging.getLogger(__name__)


event_name_to_type = {
    "bgp": BGPEvent,
    "bfd": BFDEvent,
    "reachability": ReachabilityEvent,
    "alarm": AlarmEvent,
    "portstate": PortStateEvent,
}


def set_event_state(
    old_state: OldState,
    new_state: ZinoState,
):
    id_to_type = {}

    # Register event type per id
    for linedata in old_state["::EventAttrs"]:
        if linedata.identifiers[0] == "type":
            id_to_type[int(linedata.identifiers[1])] = linedata.value

    for linedata in old_state["::EventAttrs"]:
        try:
            _set_event_attrs(linedata, new_state, id_to_type)
        except ValueError as e:
            _log.error(f"Error setting event attribute: {str(e)}")
    new_state.events._rebuild_indexes()


def _set_event_attrs(linedata: LineData, state: ZinoState, id_to_type: dict[int, str]):
    event_field = linedata.identifiers[0]
    event_id = int(linedata.identifiers[1])
    state.events.last_event_id = max(state.events.last_event_id, event_id)
    if event_id in state.events.events:
        event = state.events.events[event_id]
    else:
        event_type = id_to_type[event_id]
        event_class = event_name_to_type[event_type]
        # router needs to be set now since its a required field, will be overwritten later
        event = event_class(id=event_id, router="placeholder")
    if event_field == "priority":
        event.priority = int(linedata.value)
    elif event_field == "history":
        event.history = parse_log_and_history(linedata.value)
    elif event_field == "bgpOS":
        event.operational_state = BGPOperState(linedata.value)
    elif event_field == "bgpAS":
        event.admin_status = BGPAdminStatus(linedata.value)
    elif event_field == "lastevent":
        event.lastevent = linedata.value
    elif event_field == "log":
        event.log = parse_log_and_history(linedata.value)
    elif event_field == "polladdr":
        event.polladdr = parse_ip(linedata.value)
    elif event_field == "opened":
        event.opened = datetime.fromtimestamp(int(linedata.value), tz=timezone.utc)
    elif event_field == "peer-uptime":
        event.peer_uptime = int(linedata.value)
    elif event_field == "remote-AS":
        event.remote_as = int(linedata.value)
    elif event_field == "remote-addr":
        event.remote_address = parse_ip(linedata.value)
    elif event_field == "router":
        event.router = linedata.value
    elif event_field == "state":
        event.state = EventState(linedata.value)
    elif event_field == "updated":
        event.updated = datetime.fromtimestamp(int(linedata.value), tz=timezone.utc)
    elif event_field == "ac-down":
        event.ac_down = timedelta(seconds=int(linedata.value))
    elif event_field == "descr":
        event.descr = linedata.value
    elif event_field == "flaps":
        event.flaps = int(linedata.value)
    elif event_field == "flapstate":
        event.flapstate = FlapState(linedata.value)
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
        event.lasttrans = datetime.fromtimestamp(int(linedata.value), tz=timezone.utc)
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
