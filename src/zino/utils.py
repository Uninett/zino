import asyncio
import logging
import os
import stat
from functools import wraps
from ipaddress import ip_address
from time import time
from typing import Optional, Union

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


def log_time_spent(logger: Union[logging.Logger, str] = __name__, level: int = logging.DEBUG):
    """Decorator that logs the time taken for a function to execute.  Not suitable for use with async functions"""
    if isinstance(logger, str):
        logger = logging.getLogger(logger)

    def actual_decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time()
            try:
                result = func(*args, **kwargs)
            finally:
                end = time()
                logger.log(level, "%s took %s seconds", func.__name__, end - start)
            return result

        return wrapper

    return actual_decorator


def file_is_world_readable(file: str) -> bool:
    """Returns a boolean value indicating if a file is readable by other users than its owner"""
    st_mode = getattr(os.stat(path=file), "st_mode", None)

    return bool(st_mode & stat.S_IROTH)
