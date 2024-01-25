import argparse
import logging
from datetime import datetime, timedelta
from ipaddress import ip_address
from typing import List, get_args

from zino.events import EventIndex
from zino.linedata import LineData, get_line_data
from zino.state import ZinoState
from zino.statemodels import (
    CISCO_ENTERPRISE_ID,
    JUNIPER_ENTERPRISE_ID,
    AlarmEvent,
    AlarmType,
    BFDEvent,
    BFDSessState,
    BFDState,
    BGPEvent,
    EventState,
    InterfaceState,
    IPAddress,
    LogEntry,
    Port,
    PortOrIPAddress,
    PortStateEvent,
    ReachabilityEvent,
)

_log = logging.getLogger(__name__)

EventIndices = dict[str, EventIndex]

event_name_to_type = {
    "bgp": BGPEvent,
    "bfd": BFDEvent,
    "reachability": ReachabilityEvent,
    "alarm": AlarmEvent,
    "portstate": PortStateEvent,
}


def create_state(old_state_file: str) -> ZinoState:
    new_state = ZinoState()
    event_attrs = []
    bfd_sess_addr = []
    bfd_sess_discr = []
    event_indices: EventIndices = {}
    old_state_lines = read_file_lines(old_state_file)
    for line in old_state_lines:
        # these lines do not contain any information
        if "global" in line:
            continue
        linedata = get_line_data(line)
        if "::BootTime" in line:
            set_boot_time(linedata, new_state)
        elif "::pm::lastid" in line:
            set_last_id(linedata, new_state)
        elif "::EventAttrs" in line:
            # Parse later, need to parse ::EventIdToIx first
            event_attrs.append(linedata)
        elif "::EventIdToIx" in line:
            event_id, event_index = get_event_index(linedata)
            event_indices[event_id] = event_index
        elif "::bfdSessState" in line:
            set_bfd_sess_state(linedata, new_state)
        elif "::bfdSessAddr" in line:
            if "::bfdSessAddrType" in line:
                continue
            else:
                # bfdSessState has to be parsed first
                bfd_sess_addr.append(linedata)
        elif "::bfdSessDiscr" in line:
            # bfdSessState has to be parsed first
            bfd_sess_discr.append(linedata)
        elif "::JNXalarms" in line:
            set_jnx_alarms(linedata, new_state)
        elif "::portState" in line:
            set_port_state(linedata, new_state)
        elif "::portToIfDescr" in line:
            set_port_to_if_descr(linedata, new_state)
        elif "::portToLocIfDescr" in line:
            set_port_to_loc_if_descr(linedata, new_state)
        elif "::bgpPeerAdminState":
            set_bgp_peer_admin_state(linedata, new_state)
        elif "::bgpPeerOperState" in line:
            set_bgp_peer_oper_state(linedata, new_state)
        elif "::bgpPeerUpTime" in line:
            set_bgp_peer_up_time(linedata, new_state)
        elif "::bgpPeers" in line:
            set_bgp_peers(linedata, new_state)
        elif "::firstFlap" in line:
            set_first_flap(linedata, new_state)
        elif "::flapHistVal" in line:
            set_flap_hist_val(linedata, new_state)
        elif "::flappedAboveThreshold" in line:
            set_flapped_above_threshold(linedata, new_state)
        elif "::flapping" in line:
            set_flapping(linedata, new_state)
        elif "::flaps" in line:
            set_flaps(linedata, new_state)
        elif "::lastFlap" in line:
            set_last_flap(linedata, new_state)
        elif "::lastAge" in line:
            set_last_age(linedata, new_state)
        elif "::localAS" in line:
            set_local_as(linedata, new_state)
        elif "::sawPeer" in line:
            set_saw_peer(linedata, new_state)
        elif "::lastTime" in line:
            set_last_time(linedata, new_state)
        elif "::runsOn" in line:
            set_runs_on(linedata, new_state)
        elif "::pm_events" in line:
            set_pm_events(linedata, new_state)
        elif "::AddrToRouter" in line:
            set_addr_to_router(linedata, new_state)
    for linedata in event_attrs:
        set_event_attrs(linedata, new_state, event_indices)
    for linedata in bfd_sess_addr:
        set_bfd_sess_addr(linedata, new_state)
    for linedata in bfd_sess_discr:
        set_bfd_sess_discr(linedata, new_state)
    return new_state


def parse_ip(ip: str) -> IPAddress:
    try:
        return ip_address(ip)
    except ValueError:
        if ":" in ip:
            ip = bytes(int(i, 16) for i in ip.split(":"))
            return ip_address(ip)
        else:
            raise


def read_file_lines(file: str):
    with open(file, "r", encoding="latin-1") as state_file:
        lines = state_file.read().splitlines()
    return lines


def set_boot_time(linedata: LineData, state: ZinoState):
    device = state.devices.get(linedata.identifiers[0])
    timestamp = int(linedata.value)
    device.boot_time = datetime.fromtimestamp(timestamp)


def get_event_index(line: LineData) -> tuple[int, EventIndex]:
    """Parses a LineData representing an EventIdToIx line and returns a tuple
    of event_id, event_index
    """
    event_id = int(line.identifiers[0])
    device, port_or_ip, event_type = tuple(line.value.split(","))
    port_or_ip = parse_port_or_ip(port_or_ip)
    event_index = EventIndex(device, port_or_ip, event_name_to_type[event_type])
    return event_id, event_index


def parse_port_or_ip(port_or_ip: str) -> PortOrIPAddress:
    """Parses the part of a EventIdToIx line that defines the ip/port value"""
    if port_or_ip in get_args(AlarmType):
        return port_or_ip
    try:
        return parse_ip(port_or_ip)
    except ValueError:
        pass
    try:
        return int(port_or_ip)
    except ValueError:
        pass
    raise ValueError(f"Invalid PortOrIpAddress value: {port_or_ip}")


def parse_log_and_history(line: str) -> List[LogEntry]:
    return_list = []
    entries = line.split("{")
    for entry in entries:
        if not entry:
            # If just empty string caused by using .split()
            continue
        cleaned_entry = entry.replace("}", "")
        cleaned_entry_split = cleaned_entry.split()
        timestamp = cleaned_entry_split[0]
        log_msg = " ".join(cleaned_entry_split[1:])
        log_entry = LogEntry(timestamp=timestamp, message=log_msg)
        return_list.append(log_entry)
    return return_list


def set_event_attrs(linedata: LineData, state: ZinoState, indices: EventIndices):
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
        _log.info("bgpOS is not a supported event field")
    elif event_field == "bgpAS":
        _log.info("bgpAS is not a supported event field")
    elif event_field == "lastevent":
        _log.info("lastevent is not a supported event field")
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
        # event.port exists, but it does not allow strings like "ge-1/0/1"
        _log.info("port is not supported event field")
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
    state.events.events[event.id] = event


def set_jnx_alarms(linedata: LineData, state: ZinoState):
    device = state.devices.get(linedata.identifiers[0])
    alarm_type = linedata.identifiers[1]
    assert alarm_type in get_args(AlarmType)
    alarm_count = int(linedata.value)
    if not device.alarms:
        device.alarms = {}
    device.alarms[alarm_type] = alarm_count


def set_bfd_sess_addr(linedata: LineData, state: ZinoState):
    """Requires the matching Port and BFDState object to exist"""
    if not linedata.value:
        return
    device = state.devices.get(linedata.identifiers[0])
    ifindex = int(linedata.identifiers[1])
    port = device.ports[ifindex]
    port.bfd_state.session_addr = parse_ip(linedata.value)


def set_bfd_sess_state(linedata: LineData, state: ZinoState):
    device = state.devices.get(linedata.identifiers[0])
    ifindex = int(linedata.identifiers[1])
    sess_state = BFDSessState(linedata.value)
    if ifindex not in device.ports:
        device.ports[ifindex] = Port(ifindex=ifindex)
    port = device.ports[ifindex]
    if not port.bfd_state:
        port.bfd_state = BFDState(session_state=sess_state)
    port.bfd_state.session_state = sess_state


def set_bfd_sess_discr(linedata: LineData, state: ZinoState):
    """Requires the matching Port and BFDState object to exist"""
    device = state.devices.get(linedata.identifiers[0])
    ifindex = int(linedata.identifiers[1])
    port = device.ports[ifindex]
    port.bfd_state.session_discr = int(linedata.value)


def set_is_cisco(linedata: LineData, state: ZinoState):
    is_cisco = bool(int(linedata.value))
    if is_cisco:
        state.device.enterprise_id = CISCO_ENTERPRISE_ID


def set_is_juniper(linedata: LineData, state: ZinoState):
    is_juniper = bool(int(linedata.value))
    if is_juniper:
        state.device.enterprise_id = JUNIPER_ENTERPRISE_ID


def set_port_state(linedata: LineData, state: ZinoState):
    device = state.devices.get(linedata.identifiers[0])
    ifindex = int(linedata.identifiers[1])
    if ifindex not in device.ports:
        device.ports[ifindex] = Port(ifindex=ifindex)
    if linedata.value == "flapping":
        _log.info("flapping port state is not supported")
        return
    device.ports[ifindex].state = InterfaceState(linedata.value)


def set_port_to_if_descr(linedata: LineData, state: ZinoState):
    device = state.devices.get(linedata.identifiers[0])
    ifindex = int(linedata.identifiers[1])
    if ifindex not in device.ports:
        device.ports[ifindex] = Port(ifindex=ifindex)
    device.ports[ifindex].ifdescr = linedata.value


def set_port_to_loc_if_descr(linedata: LineData, state: ZinoState):
    """Sets ifalias value"""
    device = state.devices.get(linedata.identifiers[0])
    ifindex = int(linedata.identifiers[1])
    if ifindex not in device.ports:
        device.ports[ifindex] = Port(ifindex=ifindex)
    device.ports[ifindex].ifalias = linedata.value


def set_last_id(linedata: LineData, state: ZinoState):
    """this is an id related to planned maintenance"""
    _log.info("lastid is not supported")


def set_pm_events(linedata: LineData, state: ZinoState):
    """Planned Maintenance events. Not implemented yet"""
    _log.info("pm_events is not supported")


def set_addr_to_router(linedata: LineData, state: ZinoState):
    """addr is a polldevs things, so this should prob be ignored"""
    _log.info("addrToRouter is not supported")


def set_runs_on(linedata: LineData, state: ZinoState):
    """RunsOn command i think says if an interface runs on top of another interface"""
    _log.info("runsOn is not supported")


def set_last_time(linedata: LineData, state: ZinoState):
    """Dont think Zino2 supports this value"""
    _log.info("lastTime is not supported")


def set_event_close_times(linedata: LineData, state: ZinoState):
    """Dont think Zino2 supports this value"""
    _log.info("eventCloseTimes is not supported")


def set_bgp_peer_admin_state(linedata: LineData, state: ZinoState):
    """Supported soon"""
    _log.info("bgpPeerAdminState is not supported")


def set_bgp_peer_oper_state(linedata: LineData, state: ZinoState):
    """Supported soon"""
    _log.info("bgpPeerOperState is not supported")


def set_bgp_peer_up_time(linedata: LineData, state: ZinoState):
    """Supported soon"""
    _log.info("bgpPeerUpTime is not supported")


def set_bgp_peers(linedata: LineData, state: ZinoState):
    """Supported soon"""
    _log.info("bgpPeers is not supported")


def set_first_flap(linedata: LineData, state: ZinoState):
    _log.info("firstFlap is not supported")


def set_flap_hist_val(linedata: LineData, state: ZinoState):
    _log.info("flapHistVal is not supported")


def set_flapped_above_threshold(linedata: LineData, state: ZinoState):
    _log.info("flappedAboveThreshold is not supported")


def set_flapping(linedata: LineData, state: ZinoState):
    _log.info("flapping is not supported")


def set_flaps(linedata: LineData, state: ZinoState):
    _log.info("flaps is not supported")


def set_last_flap(linedata: LineData, state: ZinoState):
    _log.info("lastFlap is not supported")


def set_last_age(linedata: LineData, state: ZinoState):
    """Not sure what lastAge is"""
    _log.info("lastAgeis not supported")


def set_local_as(linedata: LineData, state: ZinoState):
    """localAS is BGP related"""
    _log.info("localAS not supported")


def set_saw_peer(linedata: LineData, state: ZinoState):
    """Timestamp for last time a BGP peer was seen"""
    _log.info("sawPeernot supported")


def get_parser():
    parser = argparse.ArgumentParser(description="Convert Zino1 state to Zino2 compatible state")
    parser.add_argument(
        "input",
        help="Absolute path to the Zino1 state you want to convert",
    )
    parser.add_argument(
        "output",
        help="Absolute path to where the new Zino2 state should be dumped",
    )
    return parser


def main():
    logging.basicConfig(format="%(message)s", level=logging.INFO)
    parser = get_parser()
    args = parser.parse_args()
    state = create_state(args.input)
    state.dump_state_to_file(args.output)


if __name__ == "__main__":
    main()
