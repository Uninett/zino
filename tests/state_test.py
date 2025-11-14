import json
import os
from datetime import datetime, timezone
from json import JSONDecodeError
from unittest.mock import patch

import pytest

from zino.events import EventIndex, Events
from zino.state import ZinoState, _find_duplicate_events, clean_state, resolve_duplicate_events
from zino.statemodels import EventState, ReachabilityEvent


def test_dump_state_to_file_should_dump_valid_json_to_file(tmp_path):
    dumpfile = tmp_path / "dump.json"
    state = ZinoState()
    state.dump_state_to_file(dumpfile)

    assert os.path.exists(dumpfile)
    with open(dumpfile, "r") as data:
        assert json.load(data)


class TestLoadStateFromFile:
    def test_should_raise_on_invalid_json(self, invalid_state_file):
        with pytest.raises(JSONDecodeError):
            ZinoState.load_state_from_file(str(invalid_state_file))

    def test_should_load_saved_state(self, valid_state_file):
        state = ZinoState.load_state_from_file(str(valid_state_file))
        assert state.events.last_event_id == 42

    def test_should_return_none_when_state_file_is_missing(self, tmp_path):
        fake_file = tmp_path / "nonexistent.json"
        assert ZinoState.load_state_from_file(str(fake_file)) is None


#
# Fixtures
#


@pytest.fixture
def valid_state_file(tmp_path):
    state_filename = tmp_path / "dump.json"
    with open(state_filename, "w") as statefile:
        statefile.write(
            """
        {
          "devices": {
            "devices": {}
          },
          "events": {
            "events": {
              "1": {
                "id": 1,
                "router": "example-gw1",
                "type": "reachability",
                "state": "open",
                "opened": "2023-12-06T17:03:38.73336Z",
                "updated": "2023-12-06T17:03:38.733633Z",
                "priority": 100,
                "log": [
                  {
                    "timestamp": "2023-12-06T17:03:38.733633Z",
                    "message": "example-gw1 no-response"
                  }
                ],
                "history": [
                  {
                    "timestamp": "2023-12-06T17:03:38.733615Z",
                    "message": "Change state to Open"
                  }
                ],
                "reachability": "no-response"
              }
            },
            "last_event_id": 42
          }
        }
        """
        )
    return state_filename


@pytest.fixture
def invalid_state_file(tmp_path):
    state_filename = tmp_path / "invalid-dump.json"
    with open(state_filename, "w") as state_file:
        state_file.write("{....")
    return state_filename


class TestFindDuplicateEvents:
    def test_it_should_return_empty_dict_when_no_duplicates(self):
        state = ZinoState()
        events = Events()

        # Add non-duplicate events
        event1 = ReachabilityEvent(id=1, router="router1")
        event1.state = EventState.OPEN
        events.events[1] = event1

        event2 = ReachabilityEvent(id=2, router="router2")
        event2.state = EventState.OPEN
        events.events[2] = event2

        events._rebuild_indexes()
        state.events = events

        duplicates = _find_duplicate_events(state)
        assert duplicates == {}

    def test_it_should_find_duplicate_events_with_same_index(self):
        state = ZinoState()
        events = Events()

        # Create two events with the same EventIndex
        event1 = ReachabilityEvent(id=1, router="router1")
        event1.state = EventState.OPEN
        event1.opened = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        events.events[1] = event1

        event2 = ReachabilityEvent(id=2, router="router1")  # Same router and type
        event2.state = EventState.OPEN
        event2.opened = datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc)
        events.events[2] = event2

        events._rebuild_indexes()
        state.events = events

        duplicates = _find_duplicate_events(state)
        assert len(duplicates) == 1

        # Check the duplicate entry
        event_index = EventIndex("router1", None, ReachabilityEvent)
        assert event_index in duplicates
        assert len(duplicates[event_index]) == 2
        assert (1, event1) in duplicates[event_index]
        assert (2, event2) in duplicates[event_index]

    def test_it_should_ignore_closed_events(self):
        state = ZinoState()
        events = Events()

        # Create two events with same index, but one is closed
        event1 = ReachabilityEvent(id=1, router="router1")
        event1.state = EventState.OPEN
        events.events[1] = event1

        event2 = ReachabilityEvent(id=2, router="router1")
        event2.state = EventState.CLOSED  # This one is closed
        events.events[2] = event2

        events._rebuild_indexes()
        state.events = events

        duplicates = _find_duplicate_events(state)
        assert duplicates == {}  # No duplicates since closed events are ignored


class TestResolveDuplicateEvents:
    def test_should_close_newer_duplicate_events(self):
        state = ZinoState()
        events = Events()

        # Create duplicate events with different timestamps
        event1 = ReachabilityEvent(id=1, router="router1")
        event1.state = EventState.OPEN
        event1.opened = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        events.events[1] = event1

        event2 = ReachabilityEvent(id=2, router="router1")
        event2.state = EventState.OPEN
        event2.opened = datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc)  # Newer
        events.events[2] = event2

        event3 = ReachabilityEvent(id=3, router="router1")
        event3.state = EventState.OPEN
        event3.opened = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)  # Newest
        events.events[3] = event3

        state.events = events

        # Run the resolver
        resolve_duplicate_events(state)

        # Check that oldest is still open, newer ones are closed
        assert event1.state == EventState.OPEN
        assert event2.state == EventState.CLOSED
        assert event3.state == EventState.CLOSED

    def test_it_should_add_log_entries_to_closed_duplicates(self):
        state = ZinoState()
        events = Events()

        # Create duplicate events
        event1 = ReachabilityEvent(id=1, router="router1")
        event1.state = EventState.OPEN
        event1.opened = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        events.events[1] = event1

        event2 = ReachabilityEvent(id=2, router="router1")
        event2.state = EventState.OPEN
        event2.opened = datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc)
        events.events[2] = event2

        events._rebuild_indexes()
        state.events = events

        # Run the resolver
        resolve_duplicate_events(state)

        # Check that closed event has appropriate log entry
        assert len(event2.log) == 1
        assert "duplicate of event 1" in event2.log[0].message

    def test_it_should_add_history_entry_to_closed_duplicates(self):
        state = ZinoState()
        events = Events()

        # Create duplicate events
        event1 = ReachabilityEvent(id=1, router="router1")
        event1.state = EventState.OPEN
        event1.opened = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        events.events[1] = event1

        event2 = ReachabilityEvent(id=2, router="router1")
        event2.state = EventState.OPEN
        event2.opened = datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc)
        events.events[2] = event2

        events._rebuild_indexes()
        state.events = events

        # Run the resolver
        resolve_duplicate_events(state)

        # Check that closed event has appropriate history entry
        assert len(event2.history) == 1
        assert "state change open -> closed (duplicate)" in event2.history[0].message

    def test_give_no_duplicates_it_should_not_modify_state(self):
        state = ZinoState()
        events = Events()

        # Add non-duplicate events
        event1 = ReachabilityEvent(id=1, router="router1")
        event1.state = EventState.OPEN
        events.events[1] = event1

        event2 = ReachabilityEvent(id=2, router="router2")
        event2.state = EventState.OPEN
        events.events[2] = event2

        events._rebuild_indexes()
        state.events = events

        # Run the resolver
        resolve_duplicate_events(state)

        # Check that nothing changed
        assert event1.state == EventState.OPEN
        assert event2.state == EventState.OPEN
        assert len(event1.log) == 0
        assert len(event2.log) == 0


class TestCleanState:
    def test_it_should_call_resolve_duplicate_events(self):
        state = ZinoState()

        with patch("zino.state.resolve_duplicate_events") as mock_resolve:
            clean_state(state)
            mock_resolve.assert_called_once_with(state)
