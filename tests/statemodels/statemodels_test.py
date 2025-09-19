import datetime
import json
import os

import pytest

from zino.statemodels import (
    DeviceState,
    DeviceStates,
    Event,
    EventState,
    LogEntry,
    ReachabilityEvent,
    regex_search,
)
from zino.time import now


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

    def test_model_dump_simple_attrs_should_replace_underscores_with_dashes_in_attr_names(self, fake_event):
        """Legacy Zino protocol event attributes use dashes, not underscores in their names."""
        fake_event.ac_down = datetime.timedelta(seconds=42)
        attrs = fake_event.model_dump_simple_attrs()

        assert "ac_down" not in attrs
        assert "ac-down" in attrs

    def test_model_dump_simple_attrs_should_represent_timedeltas_as_number_of_seconds(self, fake_event):
        """Legacy Zino protocol event attributes use dashes, not underscores in their names."""
        fake_event.ac_down = datetime.timedelta(seconds=42)
        attrs = fake_event.model_dump_simple_attrs()

        assert attrs["ac-down"] == "42"

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

    def test_when_set_state_is_called_it_should_change_state(self, fake_event):
        fake_event.set_state(EventState.CLOSED, user="nobody")
        assert fake_event.state == EventState.CLOSED

    def test_when_state_is_changed_set_state_should_add_history_entry(self, fake_event):
        history_count_before = len(fake_event.history)
        fake_event.set_state(EventState.CLOSED, user="nobody")
        history_count_after = len(fake_event.history)
        assert history_count_after > history_count_before

    def test_when_state_is_changed_set_state_should_add_history_entry_with_details(self, fake_event):
        old_state = fake_event.state
        fake_event.set_state(EventState.CLOSED, user="zaphod")
        last_history_entry = fake_event.history[-1]

        for detail in (old_state.value, EventState.CLOSED.value, "zaphod"):
            assert detail in last_history_entry.message

    def test_when_state_is_unchanged_set_state_should_not_add_history_entry(self, fake_event):
        history_count_before = len(fake_event.history)
        fake_event.set_state(fake_event.state, user="nobody")
        history_count_after = len(fake_event.history)
        assert history_count_after == history_count_before

    def test_get_changed_fields_should_correctly_detect_changed_fields(self, fake_event):
        copy = fake_event.model_copy(deep=True)
        copy.add_log("test")
        copy.updated = now() + datetime.timedelta(seconds=3)

        changed = fake_event.get_changed_fields(copy)
        assert set(changed) == {"log", "updated"}

    def test_dump_event_to_file_should_dump_valid_json_to_file(self, tmp_path, fake_event):
        fake_event.set_state(EventState.CLOSED)
        fake_event.dump_event_to_file(tmp_path)

        dumpfile = f"{tmp_path}/{fake_event.id}.json"
        assert os.path.exists(dumpfile)
        with open(dumpfile, "r") as data:
            assert json.load(data)


class TestLogEntryModelDumpLegacy:
    def test_should_be_prefixed_by_timestamp(self):
        entry = LogEntry(message="foobar")
        lines = entry.model_dump_legacy()
        timestamp, message = lines[0].split(" ")

        assert timestamp.isdigit()
        assert message == "foobar"

    def test_when_message_is_single_line_it_should_return_a_single_line(self):
        entry = LogEntry(message="foobar")
        lines = entry.model_dump_legacy()

        assert len(lines) == 1

    def test_when_message_is_multi_line_it_should_return_the_correct_number_of_lines(self):
        entry = LogEntry(message="one\ntwo\nthree")
        lines = entry.model_dump_legacy()

        assert len(lines) == 3

    def test_when_message_is_multi_line_continuation_lines_should_be_prefixed_by_space(self):
        entry = LogEntry(message="one\ntwo\nthree")
        lines = entry.model_dump_legacy()

        assert all(line.startswith(" ") for line in lines[1:])


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


class TestRegexSearch:
    def test_when_string_matches_not_at_the_beginning_it_should_return_true(self):
        assert regex_search("device", "blabla_device")

    def test_when_string_matches_at_the_beginning_it_should_return_true(self):
        assert regex_search("device", "device")

    def test_when_string_does_not_match_it_should_return_false(self):
        assert not regex_search("device", "wrong")


@pytest.fixture
def fake_event() -> ReachabilityEvent:
    return ReachabilityEvent(id=42, router="example-gw.example.org", state=EventState.OPEN)
