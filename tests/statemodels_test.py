import datetime

import pytest

from zino.statemodels import DeviceState, DeviceStates, EventState, ReachabilityEvent


class TestEvent:
    def test_add_log_should_set_proper_timestamp(self, fake_event):
        log = fake_event.add_log("test")
        assert isinstance(log.timestamp, datetime.datetime)

    def test_add_history_should_set_proper_timestamp(self, fake_event):
        log = fake_event.add_history("test")
        assert isinstance(log.timestamp, datetime.datetime)


class TestDeviceState:
    @pytest.mark.parametrize(
        "enterprise_id,property_name,expected",
        [(9, "is_cisco", True), (666, "is_cisco", False), (2626, "is_juniper", True), (666, "is_juniper", False)],
    )
    def test_vendor_utility_property_returns_expected_result(self, enterprise_id, property_name, expected):
        dev = DeviceState(name="foo", enterprise_id=enterprise_id)
        assert getattr(dev, property_name) == expected


class TestDeviceStates:
    def test_empty_dict_should_not_contain_devices(self):
        states = DeviceStates()
        assert len(states) == 0
        assert "foo" not in states

    def test_get_should_create_new_device_state(self):
        states = DeviceStates()
        router = "new"
        assert router not in states

        result = states.get(router)
        assert isinstance(result, DeviceState)
        assert router in states


@pytest.fixture
def fake_event():
    yield ReachabilityEvent(id=42, router="example-gw.example.org", state=EventState.OPEN)
