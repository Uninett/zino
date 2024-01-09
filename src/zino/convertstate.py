import argparse
from dataclasses import dataclass
from datetime import datetime
from ipaddress import ip_address
from typing import Optional

from zino.events import EventIndex
from zino.state import ZinoState
from zino.statemodels import (
    AlarmEvent,
    BFDEvent,
    BGPEvent,
    PortStateEvent,
    ReachabilityEvent,
)

EventIndices = dict[str, EventIndex]

event_name_to_type = {
    "bgp": BGPEvent,
    "bfd": BFDEvent,
    "reachability": ReachabilityEvent,
    "alarm": AlarmEvent,
    "portstate": PortStateEvent,
}


@dataclass
class LineData:
    """Flexible definition of the value and identifiers found in a Zino1 .tcl state dump.
    Each line in the state dump can contain several identifiers but there is always only one value.
    ex: set ::bfdSessAddr(random-gw1, 3) "AA:BB:CC:DD" means interface with index 3 for device
    random-gw1 should have a bfd session address value of AA:BB:CC:DD.
    The identifiers here are random-gw1 and 3, while the value is AA:BB:CC:DD.
    It is also possible for there to be no identifiers if it is a global value
    It is up to the user of this dataclass to know what the indentifiers and values represent.
    """

    identifiers: Optional[tuple[str, ...]]
    value: str


def convert(old_state_file: str):
    new_state = ZinoState()
    event_attrs = []
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
            # Parse later, need to parse ::EventId first
            event_attrs.append(linedata)
        elif "::EventIdToIx" in line:
            event_id, event_index = get_event_index(linedata)
            event_indices[event_id] = event_index
        else:
            pass
    for linedata in event_attrs:
        set_event_attrs(linedata, new_state, event_indices)
    print(new_state.events)


def read_file_lines(file: str):
    with open(file, "r", encoding="latin-1") as state_file:
        lines = state_file.read().splitlines()
    return lines


def get_line_data(line) -> LineData:
    """Parses a line from a Zino1 .tcl filedump into a LineData object
    containing useful information
    """
    try:
        identifiers = get_identifiers(line)
    except IndexError:
        identifiers = None
    value = get_value(line)
    return LineData(value=value, identifiers=identifiers)


def get_identifiers(line: str) -> tuple[str, ...]:
    # removes part of line before identifiers are defined
    split_line = line.split("(")[1]
    # removes everything after the identifiers
    split_line = split_line.split(")")[0]
    identifiers = split_line.split(",")
    if "EventAttrs" in line:
        # remove everything before the event ID starts
        event_line = line.split("_")[1]
        # remove everything after event ID
        event_id = event_line.split("(")[0]
        identifiers.append(event_id)
    return tuple(identifiers)


def get_value(line: str) -> str:
    # remove everything before the value is defined
    value = line.split('"')[1]
    # strip whitespace and quotes
    value = value.strip(' "')
    return value


def addr_to_router(state, line):
    # addr is a polldevs things, so this should prob be ignored
    pass


def runs_on():
    # RunsOn command i think says if an interface runs on top of another interface
    pass


def set_boot_time(linedata: LineData, state: ZinoState):
    device = state.devices.get(linedata.identifiers[0])
    timestamp = int(linedata.value)
    device.boot_time = datetime.fromtimestamp(timestamp)


def get_event_index(line: LineData) -> tuple[str, EventIndex]:
    """Parses a LineData representing an EventIdToIx line and returns a tuple
    of event_id, event_index
    """
    event_id = line.identifiers[0]
    device, ip_or_port, event_type = tuple(line.value.split(","))
    if ":" in ip_or_port:
        ip_or_port = ip_address(bytes(int(i, 16) for i in ip_or_port.split(":")))
    event_index = EventIndex(device, ip_or_port, event_name_to_type[event_type])
    return event_id, event_index


def set_event_attrs(linedata: LineData, state, indices):
    event_field = linedata.identifiers[0]
    event_id = linedata.identifiers[1]
    event_index = indices[event_id]
    event, _ = state.events.get_or_create_event(*event_index)
    if event_field == "priority":
        event.priority = linedata.value
    if event_field == "history":
        pass
    if event_field == "bgpOS":
        pass
    if event_field == "bgpAS":
        pass
    if event_field == "lastevent":
        pass
    if event_field == "log":
        pass
    if event_field == "polladdr":
        pass
    if event_field == "opened":
        pass
    if event_field == "peer-uptime":
        pass
    if event_field == "remote-AS":
        pass
    if event_field == "remote-addr":
        pass
    if event_field == "router":
        pass
    if event_field == "state":
        pass
    if event_field == "updated":
        pass
    if event_field == "ac-down":
        pass
    if event_field == "descr":
        pass
    if event_field == "flaps":
        pass
    if event_field == "flapstate":
        pass
    if event_field == "ifindex":
        pass


def set_last_id(linedata: LineData, state):
    state.events.last_event_id = int(linedata.value)


def set_last_time(state, linedata):
    # Dont think Zino2 supports this value
    pass


def event_close_times():
    pass


def event_id_to_ix():
    pass


def jnx_alarms():
    pass


def bfd_sess_addr():
    pass


def bfd_sess_addr_type():
    pass


"""


def get_line_data(line) -> LineData:
    removed_function = line.split('(')
    try:
        identifiers = line.split('(')[1]
    except IndexError:
        removed_function
    split_id_from_value = removed_function.split(')')
    identifiers = split_id_from_value[0].split(',')
    # strips whitespace and double quotes from beginning and end of string
    value = split_id_from_value[1].strip(' "')
    return LineData(value=value, identifiers=tuple(identifiers))
bfdSessDiscr

bfdSessDiscr

bgpPeerAdminState

bgpPeerOperState

bgpPeerUpTime

bgpPeers

firstFlap

flapHistVal

flappedAboveThreshold

flapping

flaps

isCisco

isJuniper

lastAge

lastFlap

localAS

lastid

lasttime

pm_events

portState

portToIfDescr

portToLocIfDescr

sawPeer
"""


def get_parser():
    parser = argparse.ArgumentParser(description="Convert Zino1 state to Zino2 compatible state")
    parser.add_argument(
        "statedump",
        help="Absolute path to the Zino1 state you want to convert",
    )
    return parser


def main():
    parser = get_parser()
    args = parser.parse_args()
    convert(args.statedump)


if __name__ == "__main__":
    main()
