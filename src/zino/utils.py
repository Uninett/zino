from ipaddress import ip_address

from pyasn1.type.univ import OctetString

from zino.statemodels import IPAddress


def parse_ip(ip: str) -> IPAddress:
    """Parses IPv4 and IPv6 addresses in different formats"""
    try:
        return ip_address(ip)
    except ValueError:
        if ip.startswith("0x"):
            return _parse_hexa_string_ip(ip)
        if ":" in ip:
            return _parse_colon_separated_ip(ip)
        raise ValueError(f"Input {ip} could not be converted to IP address.")


def _parse_hexa_string_ip(ip: str) -> IPAddress:
    """Parses IP addresses formatted as hexastrings, e.g. 0x7f000001"""
    if len(ip) == 10:
        # IPv4 address
        address_str = ".".join((map(str, OctetString(hexValue=ip[2:]).asNumbers())))
    elif len(ip) == 34:
        # IPv6 address
        address_str = ":".join(["".join(item) for item in zip(*[iter(ip[2:])] * 4)])
    else:
        raise ValueError(f"Input {ip} could not be converted to an IP address.")
    return ip_address(address_str)


def _parse_colon_separated_ip(ip: str) -> IPAddress:
    """Parses IP addresses formatted with a colon symbol separating every octet, e.g. 7F:00:00:01
    Works for both IPv6 and IPv4 addresses with the same format
    """
    return ip_address(bytes(OctetString(hexValue=ip.replace(":", ""))))
