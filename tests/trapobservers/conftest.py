"""Common fixtures for trap tests"""

import ipaddress

import pytest

from zino.statemodels import DeviceState
from zino.trapd.base import TrapOriginator


@pytest.fixture
def localhost_trap_originator():
    addr = ipaddress.IPv4Address("127.0.0.1")
    device = DeviceState(name="localhost", addresses=set((addr,)))
    return TrapOriginator(address=addr, port=162, device=device)
