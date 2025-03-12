"""Zino SNMP trap daemon back-ends"""

import importlib
from types import ModuleType

_selected_backend = None
_BACKEND_MAP = {"pysnmp": "pysnmp_backend", "netsnmp": "netsnmpy_backend", None: "netsnmpy_backend"}


def import_trap_backend(backend: str = None) -> ModuleType:
    """Import and return the selected SNMP trap back-end. The first time this is
    called, the back-end is selectable, but defaults to "netsnmp".  Subsequent calls
    that omit backend will return the back-end that was selected by the first call.
    """
    global _selected_backend, _snmp

    if backend is None and _selected_backend is not None:
        return _selected_backend

    module_name = _BACKEND_MAP.get(backend)
    if not module_name:
        raise ValueError(f"Unknown SNMP trap backend: {backend}")

    module = importlib.import_module(f"zino.trapd.{module_name}")
    if _selected_backend is None:
        _selected_backend = module
        # Hack to import all public symbols from the module into the current namespace
        globals().update({name: getattr(module, name) for name in dir(module) if not name.startswith("_")})
    return module
