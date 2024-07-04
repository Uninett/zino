from collections import defaultdict
from ipaddress import ip_address

from zino.stateconverter.linedata import LineData, get_line_data
from zino.statemodels import IPAddress

OldState = defaultdict[str, list[LineData]]


def parse_ip(ip: str) -> IPAddress:
    try:
        return ip_address(ip)
    except ValueError:
        if ":" in ip:
            ip = bytes(int(i, 16) for i in ip.split(":"))
            return ip_address(ip)
        else:
            raise


def load_state_to_dict(file: str) -> OldState:
    state_dict = defaultdict(list)
    lines = _read_file_lines(file)
    for line in lines:
        # these lines do not contain any information
        if not line.startswith("set"):
            continue
        linedata = get_line_data(line)
        var_name = _get_var_name(line)
        state_dict[var_name].append(linedata)
    return state_dict


def _get_var_name(line) -> str:
    split_line = line.split()
    var = split_line[1].split("(")[0]
    if "::EventAttrs_" in var or "::pm::event_" in var:
        var = var.split("_")[0]
    return var


def _read_file_lines(file: str):
    with open(file, "r", encoding="latin-1") as state_file:
        lines = state_file.read().splitlines()
    return lines
