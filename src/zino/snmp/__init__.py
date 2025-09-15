"""Zino SNMP back-ends"""

import importlib
import logging
import os.path
from types import ModuleType
from typing import TYPE_CHECKING
from weakref import WeakValueDictionary

from zino.config.models import PollDevice
from zino.snmp.base import SNMPBackendNotLoaded

if TYPE_CHECKING:
    from zino.snmp.pysnmp_backend import SNMP


_logger = logging.getLogger(__name__)
_snmp_sessions = WeakValueDictionary()
_selected_backend = None
_BACKEND_MAP = {"pysnmp": "pysnmp_backend", "netsnmp": "netsnmpy_backend", None: "netsnmpy_backend"}


def import_snmp_backend(backend: str = None) -> ModuleType:
    """Import and return the selected SNMP back-end. The first time this is called,
    the back-end is selectable, but defaults to "netsnmp".  Subsequent calls that omit backend will
    return the back-end that was selected by the first call.
    """
    global _selected_backend, _snmp

    if backend is None and _selected_backend is not None:
        return _selected_backend

    module_name = _BACKEND_MAP.get(backend)
    if not module_name:
        raise ValueError(f"Unknown SNMP backend: {backend}")

    _logger.info("Loading SNMP backend: %s (%s)", backend, module_name)
    module = importlib.import_module(f"zino.snmp.{module_name}")
    if _selected_backend is None:
        _selected_backend = module
        # Hack to import all public symbols from the module into the current namespace
        globals().update({name: getattr(module, name) for name in dir(module) if not name.startswith("_")})
    return module


def get_snmp_session(device: PollDevice) -> "SNMP":
    """Create or re-use an existing SNMP session for a device.

    This keeps a registry of existing/re-usable SNMP sessions so we avoid duplicate instances and over-use of sockets
    """
    global _selected_backend
    if _selected_backend is None:
        raise SNMPBackendNotLoaded()

    if _snmp_sessions is None:  # Tests suite may disable session re-use
        return _selected_backend.SNMP(device)
    # We generate a session key based on every attribute that affects how the SNMP session is set up:
    key = (device.address, device.community, device.snmpversion)
    session = _snmp_sessions.get(key)
    if not session:
        session = _snmp_sessions[key] = _selected_backend.SNMP(device)
    return session


def get_vendored_mib_directory():
    """Returns the path to the vendored MIB directory"""
    return os.path.join(os.path.dirname(__file__), "mibs")
