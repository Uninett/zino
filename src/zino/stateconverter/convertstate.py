import argparse
import logging
from collections import defaultdict

from zino.state import ZinoState
from zino.stateconverter.bfd_converter import set_bfd_state
from zino.stateconverter.linedata import LineData, get_line_data
from zino.stateconverter.utils import OldState
from zino.statemodels import CISCO_ENTERPRISE_ID, JUNIPER_ENTERPRISE_ID


def create_state(old_state_file: str) -> ZinoState:
    new_state = ZinoState()
    # Default to empty list so it does not crash if statedump doesnt contain every variable
    old_state: OldState = defaultdict(list, load_state_to_dict(old_state_file))

    set_bfd_state(old_state, new_state)

    # Set vendor state
    for linedata in old_state["::isJuniper"]:
        set_is_juniper(linedata, new_state)
    for linedata in old_state["::isCisco"]:
        set_is_cisco(linedata, new_state)

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


def load_state_to_dict(file: str) -> dict[str, list[LineData]]:
    state_dict = {}
    lines = read_file_lines(file)
    for line in lines:
        # these lines do not contain any information
        if not line.startswith("set"):
            continue
        linedata = get_line_data(line)
        var_name = get_var_name(line)
        if var_name not in state_dict:
            state_dict[var_name] = []
        state_dict[var_name].append(linedata)
    return state_dict


def get_var_name(line) -> str:
    split_line = line.split()
    var = split_line[1].split("(")[0]
    if "::EventAttrs_" in var:
        var = var.split("_")[0]
    return var


def read_file_lines(file: str):
    with open(file, "r", encoding="latin-1") as state_file:
        lines = state_file.read().splitlines()
    return lines


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
