"""Zino SNMP back-ends"""

from weakref import WeakValueDictionary

from zino.config.models import PollDevice

# Select one of the two SNMP back-ends:
# from .pysnmp_backend import *  # noqa
from .netsnmpy_backend import *  # noqa
from .netsnmpy_backend import SNMP

_snmp_sessions = WeakValueDictionary()


def get_snmp_session(device: PollDevice) -> SNMP:
    """Create or re-use an existing SNMP session for a device.

    This keeps a registry of existing/re-usable SNMP sessions so we avoid duplicate instances and over-use of sockets
    """
    if _snmp_sessions is None:  # Tests suite may disable session re-use
        return SNMP(device)
    # We generate a session key based on every attribute that affects how the SNMP session is set up:
    key = (device.address, device.community, device.hcounters)
    session = _snmp_sessions.get(key)
    if not session:
        session = _snmp_sessions[key] = SNMP(device)
    return session
