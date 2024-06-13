"""Tests for functions that are unchanged in subclasses of PlannedMaintenance"""

import datetime

import pytest

from zino.statemodels import EventState, PlannedMaintenance, ReachabilityEvent


class TestEnd:
    def test_should_set_state_to_open_for_all_events_in_events_id_list(self, state, reachability_event, pm):
        reachability_event.state = EventState.IGNORED
        state.events.commit(reachability_event)
        pm.event_ids.append(reachability_event.id)
        pm.end(state)
        assert state.events.get(reachability_event.router, None, ReachabilityEvent).state is EventState.OPEN


class TestAddLog:
    def test_should_add_log_entry_to_log_list_with_correct_message(self, pm):
        msg = "log msg"
        entry = pm.add_log(msg)
        assert entry.message == msg
        assert entry in pm.log


@pytest.fixture
def pm() -> PlannedMaintenance:
    return PlannedMaintenance(
        start_time=datetime.datetime.now() - datetime.timedelta(days=1),
        end_time=datetime.datetime.now() + datetime.timedelta(days=1),
        type="device",
        match_type="str",
        match_expression="device",
        match_device=None,
    )
