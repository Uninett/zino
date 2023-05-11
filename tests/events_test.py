import pytest

from zino.events import EventExistsError, Events
from zino.statemodels import Event, ReachabilityEvent


class TestEvents:
    def test_initial_events_should_be_empty(self):
        events = Events()
        assert len(events) == 0

    def test_create_event_should_return_event(self):
        events = Events()
        event = events.create_event("foobar", None, ReachabilityEvent)

        assert event.id > 0

    def test_event_registry_should_contain_one_event_when_first_event_is_created(self):
        events = Events()
        events.create_event("foobar", None, ReachabilityEvent)

        assert len(events) == 1

    def test_adding_two_identical_events_should_raise(self):
        events = Events()
        events.create_event("foobar", None, ReachabilityEvent)

        with pytest.raises(EventExistsError):
            events.create_event("foobar", None, ReachabilityEvent)

    def test_event_should_be_gettable_by_id(self):
        events = Events()
        event = events.create_event("foobar", None, ReachabilityEvent)

        assert events[event.id] == event

    def test_get_or_create_event_should_return_new_event(self):
        events = Events()
        event, created = events.get_or_create_event("foobar", None, ReachabilityEvent)

        assert created
        assert isinstance(event, Event)

    def test_get_or_create_event_should_return_existing_event_on_same_index(self):
        events = Events()
        event1, created1 = events.get_or_create_event("foobar", None, ReachabilityEvent)
        event2, created2 = events.get_or_create_event("foobar", None, ReachabilityEvent)

        assert event2 is event1
