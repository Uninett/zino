import datetime
from unittest.mock import patch

import pytest

from zino.statemodels import (
    EventState,
    MatchType,
    PortStateEvent,
    PortstateMaintenance,
    ReachabilityEvent,
)


class TestStart:
    def test_should_set_state_of_matching_events_to_ignored(self, state, portstate_event, matching_portstate_pm):
        assert portstate_event.state is EventState.OPEN
        matching_portstate_pm.start(state)
        assert (
            state.events.get(portstate_event.router, portstate_event.subindex, PortStateEvent).state
            is EventState.IGNORED
        )

    def test_should_add_started_events_to_event_ids_list(self, state, portstate_event, matching_portstate_pm):
        assert portstate_event.id not in matching_portstate_pm.event_ids
        matching_portstate_pm.start(state)
        assert portstate_event.id in matching_portstate_pm.event_ids

    def test_should_not_change_state_of_events_that_are_not_portstate_events(
        self, state, reachability_event, matching_portstate_pm
    ):
        assert reachability_event.state is EventState.OPEN
        matching_portstate_pm.start(state)
        assert (
            state.events.get(reachability_event.router, reachability_event.subindex, ReachabilityEvent).state
            is EventState.OPEN
        )

    def test_should_create_matching_event_with_ignored_state_if_it_does_not_exist(
        self, state, device, port, matching_portstate_pm
    ):
        assert not state.events.get(device.name, port.ifindex, PortStateEvent)
        matching_portstate_pm.start(state)
        created_event = state.events.get(device.name, port.ifindex, PortStateEvent)
        assert created_event
        assert created_event.state is EventState.IGNORED

    def test_should_not_change_state_of_non_matching_events(self, state, portstate_event, nonmatching_portstate_pm):
        assert portstate_event.state is EventState.OPEN
        nonmatching_portstate_pm.start(state)
        assert (
            state.events.get(portstate_event.router, portstate_event.subindex, PortStateEvent).state is EventState.OPEN
        )


class TestMatchesEvent:
    def test_should_return_true_for_matching_event(self, state, portstate_event, matching_portstate_pm):
        assert matching_portstate_pm.matches_event(portstate_event, state)

    def test_should_return_false_for_events_that_are_not_portstate_events(
        self, state, reachability_event, matching_portstate_pm
    ):
        assert not matching_portstate_pm.matches_event(reachability_event, state)

    def test_should_return_false_for_non_matching_events(self, state, reachability_event, nonmatching_portstate_pm):
        assert not nonmatching_portstate_pm.matches_event(reachability_event, state)


class TestMatchesPortstate:
    @pytest.mark.parametrize("portstate_pm", [MatchType.REGEXP, MatchType.STR, MatchType.INTF_REGEXP], indirect=True)
    def test_should_return_false_for_non_matching_port(self, portstate_pm, device, port):
        port.ifdescr = "wrongport"
        assert not portstate_pm.matches_portstate(device, port)

    @pytest.mark.parametrize("portstate_pm", [MatchType.REGEXP, MatchType.STR], indirect=True)
    def test_regexp_and_str_should_return_true_for_matching_port(self, portstate_pm, device, port):
        assert portstate_pm.matches_portstate(device, port)

    @pytest.mark.parametrize("portstate_pm", [MatchType.INTF_REGEXP], indirect=True)
    def test_intf_regexp_should_return_true_for_matching_port_and_device(self, portstate_pm, device, port):
        assert portstate_pm.matches_portstate(device, port)

    @pytest.mark.parametrize("portstate_pm", [MatchType.INTF_REGEXP], indirect=True)
    def test_intf_regexp_match_type_should_return_false_for_matching_port_and_non_matching_device(
        self, portstate_pm, device, port
    ):
        device.name = "wrongdevice"
        assert not portstate_pm.matches_portstate(device, port)

    @pytest.mark.parametrize("portstate_pm", [MatchType.EXACT], indirect=True)
    def test_should_return_false_if_invalid_match_type(self, portstate_pm, device, port):
        assert not portstate_pm.matches_portstate(device, port)


@pytest.fixture
def portstate_pm(request, device, port) -> PortstateMaintenance:
    return PortstateMaintenance(
        start_time=datetime.datetime.now() - datetime.timedelta(days=1),
        end_time=datetime.datetime.now() + datetime.timedelta(days=1),
        match_type=request.param,
        match_expression=port.ifdescr,
        match_device=device.name,
    )


@pytest.fixture
def matching_portstate_pm(device, port) -> PortstateMaintenance:
    with patch("zino.statemodels.PortstateMaintenance.matches_portstate") as mock:
        mock.return_value = True
        yield PortstateMaintenance(
            start_time=datetime.datetime.now() - datetime.timedelta(days=1),
            end_time=datetime.datetime.now() + datetime.timedelta(days=1),
            match_type="str",
            match_expression=port.ifdescr,
            match_device=device.name,
        )


@pytest.fixture
def nonmatching_portstate_pm(device, port) -> PortstateMaintenance:
    with patch("zino.statemodels.PortstateMaintenance.matches_portstate") as mock:
        mock.return_value = False
        yield PortstateMaintenance(
            start_time=datetime.datetime.now() - datetime.timedelta(days=1),
            end_time=datetime.datetime.now() + datetime.timedelta(days=1),
            match_type="str",
            match_expression=port.ifdescr,
            match_device=device.name,
        )
