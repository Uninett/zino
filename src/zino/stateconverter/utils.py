from collections import defaultdict
from ipaddress import ip_address

from zino.stateconverter.linedata import LineData
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
