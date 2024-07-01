import asyncio
from ipaddress import ip_address
from typing import Optional

import aiodns
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
    return ip_address(bytes(OctetString(hexValue=ip[2:])))


def _parse_colon_separated_ip(ip: str) -> IPAddress:
    """Parses IP addresses formatted with a colon symbol separating every octet, e.g. 7F:00:00:01"""
    return ip_address(bytes(OctetString(hexValue=ip.replace(":", ""))))


async def reverse_dns(ip: str) -> Optional[str]:
    """Returns hostname for given IP address or None if reverse DNS lookup fails"""
    loop = asyncio.get_event_loop()
    resolver = aiodns.DNSResolver(loop=loop)
    try:
        response = await resolver.gethostbyaddr(ip)
        return response.name
    except aiodns.error.DNSError:
        return None
