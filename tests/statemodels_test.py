import datetime

import pytest

from zino.statemodels import Event, EventState, EventType


class TestEvent:
    def test_add_log_should_set_proper_timestamp(self, fake_event):
        log = fake_event.add_log("test")
        assert isinstance(log.timestamp, datetime.datetime)

    def test_add_history_should_set_proper_timestamp(self, fake_event):
        log = fake_event.add_history("test")
        assert isinstance(log.timestamp, datetime.datetime)


@pytest.fixture
def fake_event():
    yield Event(id=42, router="example-gw.example.org", event_type=EventType.REACHABILITY, state=EventState.OPEN)
