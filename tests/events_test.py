from unittest.mock import Mock

import pytest

from zino.events import EventExistsError, Events
from zino.statemodels import Event, EventState, ReachabilityEvent


class TestEvents:
    def test_initial_events_should_be_empty(self):
        events = Events()
        assert len(events) == 0

    def test_create_event_should_return_event(self):
        events = Events()
        event = events.create_event("foobar", None, ReachabilityEvent)

        assert isinstance(event, ReachabilityEvent)

    def test_event_registry_should_not_contain_uncommited_event(self):
        events = Events()
        events.create_event("foobar", None, ReachabilityEvent)

        assert len(events) == 0

    def test_adding_two_identical_events_should_raise(self):
        events = Events()
        event = events.create_event("foobar", None, ReachabilityEvent)
        events.commit(event)

        with pytest.raises(EventExistsError):
            events.create_event("foobar", None, ReachabilityEvent)

    def test_event_should_be_gettable_by_id(self):
        events = Events()
        event = events.create_event("foobar", None, ReachabilityEvent)
        events.commit(event)

        assert events[event.id] == event

    def test_get_or_create_event_should_return_new_event(self):
        events = Events()
        event = events.get_or_create_event("foobar", None, ReachabilityEvent)

        assert event.id is None
        assert isinstance(event, Event)

    def test_get_or_create_event_should_return_existing_event_on_same_index(self):
        events = Events()
        event1 = events.get_or_create_event("foobar", None, ReachabilityEvent)
        events.commit(event1)
        event2 = events.get_or_create_event("foobar", None, ReachabilityEvent)

        assert event2 == event1

    def test_checkout_should_return_copy(self):
        events = Events()
        original_event = events.get_or_create_event("foobar", None, ReachabilityEvent)
        events.commit(original_event)
        copy = events.checkout(original_event.id)

        assert original_event is not copy

    def test_checkout_should_return_deep_log_copy(self):
        events = Events()
        original_event = events.get_or_create_event("foobar", None, ReachabilityEvent)
        original_event.add_log("first log")
        events.commit(original_event)

        copy = events.checkout(original_event.id)
        copy.add_log("second log")

        assert original_event.log != copy.log

    def test_commit_should_replace_event(self):
        events = Events()
        original_event = events.get_or_create_event("foobar", None, ReachabilityEvent)
        events.commit(original_event)

        copy = events.checkout(original_event.id)
        copy.add_log("this is the successor event")

        events.commit(copy)

        assert events[copy.id] is copy

    def test_commit_should_update_index(self):
        events = Events()
        original_event = events.get_or_create_event("foobar", None, ReachabilityEvent)
        events.commit(original_event)

        copy = events.checkout(original_event.id)
        copy.add_log("this is the successor event")

        events.commit(copy)

        assert events.get("foobar", None, ReachabilityEvent) is copy

    def test_commit_should_open_embryonic_event(self):
        events = Events()
        event = events.get_or_create_event("foobar", None, ReachabilityEvent)
        assert event.state == EventState.EMBRYONIC
        events.commit(event)
        assert event.state == EventState.OPEN

    def test_when_observer_is_added_it_should_be_called_on_commit(self):
        events = Events()
        observer = Mock()
        events.add_event_observer(observer.observe)
        event = events.get_or_create_event("foobar", None, ReachabilityEvent)

        events.commit(event)
        assert observer.observe.called
