from unittest.mock import Mock
from weakref import WeakValueDictionary

import pytest

import zino.snmp
from zino.config.models import PollDevice
from zino.snmp import get_snmp_session, import_snmp_backend


class TestGetSnmpSession:
    def test_it_should_return_same_session_instance_for_same_device(self, monkeypatch):
        # Temporarily enable session re-use (which is otherwise disabled for testing purposes)
        with monkeypatch.context() as patch:
            patch.setattr("zino.snmp._snmp_sessions", WeakValueDictionary())
            device = PollDevice(name="localhost", address="127.0.0.1", community="public", hcounters=True)
            session1 = get_snmp_session(device)
            session2 = get_snmp_session(device)
            assert session1 is session2

    def test_when_reuse_is_disabled_it_should_return_new_session(self):
        device = PollDevice(name="localhost", address="127.0.0.1", community="public", hcounters=True)
        session1 = get_snmp_session(device)
        session2 = get_snmp_session(device)
        assert session1 is not session2

    def test_when_backend_is_not_loaded_it_should_raise(self, monkeypatch):
        with monkeypatch.context() as patch:
            patch.setattr("zino.snmp._selected_backend", None)
            with pytest.raises(zino.snmp.SNMPBackendNotLoaded):
                get_snmp_session(Mock())


class TestImportSnmpBackend:
    def test_when_backend_is_already_selected_and_argument_is_empty_it_should_return_already_loaded_backend(self):
        assert zino.snmp._selected_backend is not None  # conftest should already have loaded a backend
        module = import_snmp_backend()
        assert module == zino.snmp._selected_backend

    def test_when_backend_is_unknown_it_should_raise_value_error(self):
        with pytest.raises(ValueError):
            import_snmp_backend("nonexistent-foobar")
