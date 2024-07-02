import argparse
import logging
from datetime import datetime
from typing import get_args

from zino.state import ZinoState
from zino.stateconverter.bfd_converter import set_bfd_state
from zino.stateconverter.bgp_converter import set_bgp_state
from zino.stateconverter.event_converter import set_event_state
from zino.stateconverter.linedata import LineData
from zino.stateconverter.port_converter import set_port_state
from zino.stateconverter.utils import load_state_to_dict, parse_ip
from zino.statemodels import CISCO_ENTERPRISE_ID, JUNIPER_ENTERPRISE_ID, AlarmType

_log = logging.getLogger(__name__)


def create_state(old_state_file: str) -> ZinoState:
    new_state = ZinoState()
    # The returned dictionary defaults to empty list, so we dont need to check if the key exists
    # or manually set default value to avoid crashing if a variable is missing in the state file
    old_state = load_state_to_dict(old_state_file)

    set_bfd_state(old_state, new_state)
    set_bgp_state(old_state, new_state)
    set_event_state(old_state, new_state)
    set_port_state(old_state, new_state)

    # Set vendor state
    for linedata in old_state["::isJuniper"]:
        set_is_juniper(linedata, new_state)
    for linedata in old_state["::isCisco"]:
        set_is_cisco(linedata, new_state)

    # Load device alarm state
    for linedata in old_state["::JNXalarms"]:
        set_jnx_alarms(linedata, new_state)

    # Load device boot time
    for linedata in old_state["::BootTime"]:
        set_boot_time(linedata, new_state)

    # Load address to router mapping
    for linedata in old_state["::AddrToRouter"]:
        set_addr_to_router(linedata, new_state)

    # Load timestamps for when events were closed
    for linedata in old_state["::EventCloseTimes"]:
        set_event_close_times(linedata, new_state)

    return new_state


def set_is_cisco(linedata: LineData, state: ZinoState):
    is_cisco = bool(int(linedata.value))
    device = state.devices.get(linedata.identifiers[0])
    if is_cisco:
        device.enterprise_id = CISCO_ENTERPRISE_ID


def set_is_juniper(linedata: LineData, state: ZinoState):
    is_juniper = bool(int(linedata.value))
    device = state.devices.get(linedata.identifiers[0])
    if is_juniper:
        device.enterprise_id = JUNIPER_ENTERPRISE_ID


def set_jnx_alarms(linedata: LineData, state: ZinoState):
    device = state.devices.get(linedata.identifiers[0])
    alarm_type = linedata.identifiers[1]
    assert alarm_type in get_args(AlarmType)
    alarm_count = int(linedata.value)
    if not device.alarms:
        device.alarms = {}
    device.alarms[alarm_type] = alarm_count


def set_boot_time(linedata: LineData, state: ZinoState):
    device = state.devices.get(linedata.identifiers[0])
    timestamp = int(linedata.value)
    device.boot_time = datetime.fromtimestamp(timestamp)


def set_addr_to_router(linedata: LineData, state: ZinoState):
    """Corresponds to ZinoState.addresses"""
    ip_string = linedata.identifiers[0]
    try:
        ip = parse_ip(ip_string)
    except ValueError:
        _log.error(f"Could not parse ip {ip_string}")
    device_name = linedata.value
    state.addresses[ip] = device_name


def set_event_close_times(linedata: LineData, state: ZinoState):
    """Records when event was closed, not currently supported in Zino2.
    Might be supported in the future.
    """
    _log.info("EventCloseTimes is not supported")


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
