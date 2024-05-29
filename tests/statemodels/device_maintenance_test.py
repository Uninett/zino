import datetime
from unittest.mock import patch

import pytest

from zino.statemodels import (
    DeviceMaintenance,
    EventState,
    MatchType,
    PortStateEvent,
    ReachabilityEvent,
)


class TestStart:
    def test_should_set_state_of_matching_events_to_ignored(self, state, reachability_event, matching_device_pm):
        assert reachability_event.state is EventState.OPEN
        matching_device_pm.start(state)
        assert state.events.get(reachability_event.router, None, ReachabilityEvent).state is EventState.IGNORED

    def test_should_add_started_events_to_event_ids_list(self, state, reachability_event, matching_device_pm):
        assert reachability_event.id not in matching_device_pm.event_ids
        matching_device_pm.start(state)
        assert reachability_event.id in matching_device_pm.event_ids

    def test_should_not_change_state_of_non_matching_events(self, state, reachability_event, nonmatching_device_pm):
        assert reachability_event.state is EventState.OPEN
        nonmatching_device_pm.start(state)
        assert state.events.get(reachability_event.router, None, ReachabilityEvent).state is EventState.OPEN

    def test_should_not_change_state_of_events_that_are_not_reachability_or_alarm_events(
        self, state, portstate_event, matching_device_pm
    ):
        assert portstate_event.state is EventState.OPEN
        matching_device_pm.start(state)
        assert (
            state.events.get(portstate_event.router, portstate_event.subindex, PortStateEvent).state is EventState.OPEN
        )

    def test_should_create_matching_event_with_ignored_state_if_it_does_not_exist(
        self, state, device, matching_device_pm
    ):
        assert not state.events.get(device.name, None, ReachabilityEvent)
        matching_device_pm.start(state)
        created_event = state.events.get(device.name, None, ReachabilityEvent)
        assert created_event
        assert created_event.state is EventState.IGNORED


class TestMatchesEvent:
    def test_should_return_true_for_matching_event(self, state, reachability_event, matching_device_pm):
        assert matching_device_pm.matches_event(reachability_event, state)

    def test_should_return_false_for_non_matching_events(self, state, reachability_event, nonmatching_device_pm):
        assert not nonmatching_device_pm.matches_event(reachability_event, state)

    def test_should_return_false_for_events_that_are_not_reachability_or_alarm_events(
        self, state, portstate_event, matching_device_pm
    ):
        assert not matching_device_pm.matches_event(portstate_event, state)


class TestMatchesDevice:
    @pytest.mark.parametrize("device_pm", [MatchType.EXACT, MatchType.REGEXP, MatchType.STR], indirect=True)
    def test_should_return_true_if_device_name_matches_expression(self, device, device_pm):
        assert device_pm.matches_device(device)

    @pytest.mark.parametrize("device_pm", [MatchType.EXACT, MatchType.REGEXP, MatchType.STR], indirect=True)
    def test_should_return_false_if_device_name_does_not_match_expression(self, device, device_pm):
        device.name = "wrongdevice"
        assert not device_pm.matches_device(device)

    @pytest.mark.parametrize("device_pm", [MatchType.INTF_REGEXP], indirect=True)
    def test_should_return_false_if_invalid_match_type(self, device, device_pm):
        assert not device_pm.matches_device(device)


@pytest.fixture
def device_pm(request, device) -> DeviceMaintenance:
    return DeviceMaintenance(
        start_time=datetime.datetime.now() - datetime.timedelta(days=1),
        end_time=datetime.datetime.now() + datetime.timedelta(days=1),
        match_type=request.param,
        match_expression=device.name,
        match_device=None,
    )


@pytest.fixture
def matching_device_pm(device, port) -> DeviceMaintenance:
    with patch("zino.statemodels.DeviceMaintenance.matches_device") as mock:
        mock.return_value = True
        yield DeviceMaintenance(
            start_time=datetime.datetime.now() - datetime.timedelta(days=1),
            end_time=datetime.datetime.now() + datetime.timedelta(days=1),
            match_type="str",
            match_expression=port.ifdescr,
            match_device=None,
        )


@pytest.fixture
def nonmatching_device_pm(device, port) -> DeviceMaintenance:
    with patch("zino.statemodels.DeviceMaintenance.matches_device") as mock:
        mock.return_value = False
        yield DeviceMaintenance(
            start_time=datetime.datetime.now() - datetime.timedelta(days=1),
            end_time=datetime.datetime.now() + datetime.timedelta(days=1),
            match_type="str",
            match_expression=port.ifdescr,
            match_device=None,
        )
