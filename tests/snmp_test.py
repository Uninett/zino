from weakref import WeakValueDictionary

from zino.config.models import PollDevice
from zino.snmp import get_snmp_session


class TestGetSnmpSession:
    def test_it_should_return_same_session_instance_for_same_device(self, monkeypatch):
        # Temporarily enable session re-use (which is otherwise disabled for testing purposes)
        with monkeypatch.context() as patch:
            patch.setattr("zino.snmp._snmp_sessions", WeakValueDictionary())
            device = PollDevice(name="localhost", address="127.0.0.1", community="public", hcounters=True)
            session1 = get_snmp_session(device)
            session2 = get_snmp_session(device)
            assert session1 is session2
