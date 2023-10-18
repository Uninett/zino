import datetime

import pytest

from zino.statemodels import (
    DeviceState,
    DeviceStates,
    Event,
    EventState,
    ReachabilityEvent,
)


class TestEvent:
    def test_add_log_should_set_proper_timestamp(self, fake_event):
        log = fake_event.add_log("test")
        assert isinstance(log.timestamp, datetime.datetime)

    def test_add_history_should_set_proper_timestamp(self, fake_event):
        log = fake_event.add_history("test")
        assert isinstance(log.timestamp, datetime.datetime)

    def test_model_dump_simple_attrs_should_return_dict_of_only_string_values(self, fake_event):
        attrs = fake_event.model_dump_simple_attrs()

        assert all(isinstance(val, str) for val in attrs.values())

    def test_model_dump_simple_attrs_should_not_return_dict_with_log_or_history(self, fake_event):
        attrs = fake_event.model_dump_simple_attrs()

        assert "log" not in attrs
        assert "history" not in attrs

    def test_zinoify_value_when_value_is_enum_it_should_return_its_real_value(self):
        assert Event.zinoify_value(EventState.OPEN) == "open"

    def test_zinoify_value_when_value_is_int_it_should_return_a_str(self):
        assert Event.zinoify_value(42) == "42"

    def test_zinoify_value_when_value_is_datetime_it_should_return_a_unix_timestamp_as_a_str(self):
        timestamp = datetime.datetime(2023, 10, 18, 11, 53, 37, tzinfo=datetime.timezone.utc)
        assert Event.zinoify_value(timestamp) == "1697630017"

    def test_zinoify_value_when_value_is_anything_its_str_should_be_returned(self):
        class Throwaway:
            def __str__(self):
                return "foo"

        assert Event.zinoify_value(Throwaway()) == "foo"


class TestDeviceState:
    @pytest.mark.parametrize(
        "enterprise_id,property_name,expected",
        [(9, "is_cisco", True), (666, "is_cisco", False), (2636, "is_juniper", True), (666, "is_juniper", False)],
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
def fake_event() -> ReachabilityEvent:
    return ReachabilityEvent(id=42, router="example-gw.example.org", state=EventState.OPEN)
