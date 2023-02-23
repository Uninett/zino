"""Zino configuration models"""
from ipaddress import IPv4Address, IPv6Address
from typing import Optional, Union

from pydantic import BaseModel

IPAddress = Union[IPv4Address, IPv6Address]


# config fields and default values from
# https://gitlab.sikt.no/verktoy/zino/blob/master/common/config.tcl#L18-44
class PollDevice(BaseModel):
    """Defines the attributes Zino needs/wants to be able to poll a device"""

    name: str
    address: IPAddress
    community: str = "public"
    dns: str = None
    interval: int = 15
    ignorepat: Optional[str] = None
    watchpat: Optional[str] = None
    priority: int = 100
    timeout: int = 5
    retries: int = 3
    domain: str = None
    statistics: bool = True
    hcounters: bool = False
    do_bgp: bool = True
    port: int = 161
