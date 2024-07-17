import ipaddress
import logging
from asyncio import Future
from datetime import timedelta
from unittest.mock import Mock

import pytest

from zino import flaps
from zino.config.models import PollDevice
from zino.flaps import (
    FLAP_CEILING,
    FLAP_INIT_VAL,
    FLAP_MIN,
    FLAP_THRESHOLD,
    FlappingState,
    FlappingStates,
    age_flapping_states,
    age_single_interface_flapping_state,
    stabilize_flapping_state,
)
from zino.state import ZinoState
from zino.statemodels import EventState, FlapState, Port, PortStateEvent
from zino.tasks.linkstatetask import LinkStateTask
from zino.time import now


class TestFlappingState:
    def test_update_should_increase_histval(self):
        flapping_state = FlappingState()
        initial = flapping_state.hist_val

        flapping_state.update()
        assert flapping_state.hist_val > initial

    def test_update_should_set_last_flap_timestamp(self):
        flapping_state = FlappingState()
        initial = now() - timedelta(seconds=10)
        flapping_state.last_flap = initial

        flapping_state.update()
        assert flapping_state.last_flap > initial

    def test_update_should_never_increase_hist_val_above_ceiling(self):
        flapping_state = FlappingState(hist_val=FLAP_CEILING)

        flapping_state.update()
        assert flapping_state.hist_val <= FLAP_CEILING

    def test_age_should_decrease_hist_val(self):
        flapping_state = FlappingState(hist_val=42)

        flapping_state.age()
        assert flapping_state.hist_val < 42

    def test_when_hist_val_is_below_threshold_is_below_threshold_should_return_true(self):
        flapping_state = FlappingState(hist_val=FLAP_THRESHOLD - 0.2)

        assert flapping_state.is_below_threshold()


class TestFlappingStates:
    def test_update_interface_flap_should_update_existing_flapping_state(self):
        flapping_states = FlappingStates()
        flapping_states.interfaces[1] = FlappingState(hist_val=42)

        flapping_states.update_interface_flap(1)
        assert flapping_states.interfaces[1].hist_val > 42

    def test_when_interface_has_no_flapping_stats_update_interface_flap_should_initialize_them(self):
        flapping_states = FlappingStates()

        flapping_states.update_interface_flap(1)
        assert 1 in flapping_states.interfaces

    def test_first_flap_should_initialize_flapping_state(self):
        flapping_states = FlappingStates()

        flapping_states.first_flap(1)
        assert flapping_states.interfaces[1].flaps == 1
        assert flapping_states.interfaces[1].hist_val == FLAP_INIT_VAL

    def test_unflap_should_remove_flapping_state(self):
        flapping_states = FlappingStates()
        flapping_states.interfaces[1] = FlappingState()

        flapping_states.unflap(1)
        assert 1 not in flapping_states.interfaces

    def test_when_hist_val_is_above_threshold_is_flapping_should_set_flag(self):
        flapping_states = FlappingStates()
        flapping_states.interfaces[1] = FlappingState(hist_val=FLAP_THRESHOLD + 0.2)

        flapping_states.is_flapping(1)
        assert flapping_states.interfaces[1].flapped_above_threshold

    def test_when_hist_val_is_above_threshold_is_flapping_should_return_true(self):
        flapping_states = FlappingStates()
        flapping_states.interfaces[1] = FlappingState(hist_val=FLAP_THRESHOLD + 0.2)

        assert flapping_states.is_flapping(1)

    def test_when_hist_val_is_below_minimal_threshold_is_flapping_should_return_false(self):
        flapping_states = FlappingStates()
        flapping_states.interfaces[1] = FlappingState(hist_val=FLAP_MIN - 0.2)

        assert not flapping_states.is_flapping(1)

    def test_when_flapping_stats_is_between_thresholds_is_flapping_should_return_false(self):
        flapping_states = FlappingStates()
        flapping_states.interfaces[1] = FlappingState(hist_val=int((FLAP_THRESHOLD + FLAP_MIN) / 2))

        assert not flapping_states.is_flapping(1)

    def test_when_flapping_stats_do_not_exist_is_flapping_should_return_false(self):
        flapping_states = FlappingStates()

        assert not flapping_states.is_flapping(1)

    def test_when_flapping_stats_exist_was_flapping_should_return_true(self):
        flapping_states = FlappingStates()
        flapping_states.interfaces[1] = FlappingState()

        assert flapping_states.was_flapping(1)

    def test_when_flapping_stats_do_not_exist_was_flapping_should_return_false(self):
        flapping_states = FlappingStates()

        assert not flapping_states.was_flapping(1)

    def test_when_flapping_stats_exist_get_flap_count_should_return_flap_count(self):
        flapping_states = FlappingStates()
        flapping_states.interfaces[1] = FlappingState(flaps=42)

        assert flapping_states.get_flap_count(1) == 42

    def test_when_flapping_stats_do_not_exist_get_flap_count_should_return_zero(self):
        flapping_states = FlappingStates()

        assert flapping_states.get_flap_count(1) == 0

    def test_when_flapping_stats_exist_get_flap_value_should_return_hist_val(self):
        flapping_states = FlappingStates()
        flapping_states.interfaces[1] = FlappingState(hist_val=42)

        assert flapping_states.get_flap_value(1) == 42

    def test_when_flapping_stats_do_not_exist_get_flap_value_should_return_zero(self):
        flapping_states = FlappingStates()

        assert flapping_states.get_flap_value(1) == 0


class TestFlappingStatesClearFlapInternal:
    def test_when_event_with_flapstate_exists_it_should_reset_it_to_stable(
        self, state_with_flapstats_and_portstate_event
    ):
        state = state_with_flapstats_and_portstate_event
        port: Port = next(iter(state.devices.devices["localhost"].ports.values()))

        state.flapping._clear_flap_internal(
            ("localhost", port.ifindex), "nobody", "Flapstate manually cleared", state=state
        )

        updated_event = state.events.get("localhost", port.ifindex, PortStateEvent)
        assert updated_event
        assert updated_event.flapstate == FlapState.STABLE

    def test_when_event_does_not_exist_it_should_do_nothing(
        self,
        state_with_flapstats,
    ):
        state = state_with_flapstats
        port: Port = next(iter(state.devices.devices["localhost"].ports.values()))

        state.flapping._clear_flap_internal(
            ("localhost", port.ifindex), "nobody", "Flapstate manually cleared", state=state
        )

        assert not state.events.get("localhost", port.ifindex, PortStateEvent)

    def test_when_event_but_not_port_exists_it_should_do_nothing(self, state_with_flapstats_and_portstate_event):
        state = state_with_flapstats_and_portstate_event
        port: Port = next(iter(state.devices.devices["localhost"].ports.values()))
        # Remove the port from device state for this test
        del state.devices.devices["localhost"].ports[port.ifindex]

        state.flapping._clear_flap_internal(
            ("localhost", port.ifindex), "nobody", "Flapstate manually cleared", state=state
        )

        event = state.events.get("localhost", port.ifindex, PortStateEvent)
        assert event
        assert event.flapstate == FlapState.FLAPPING  # still flapping!


class TestFlappingStatesClearFlap:
    def test_it_should_schedule_verification_of_single_port(
        self,
        state_with_flapstats_and_portstate_event,
        polldevs_dict,
        monkeypatch,
    ):
        state = state_with_flapstats_and_portstate_event
        port: Port = next(iter(state.devices.devices["localhost"].ports.values()))
        mock_schedule_verification_of_single_port = Mock()
        monkeypatch.setattr(
            LinkStateTask, "schedule_verification_of_single_port", mock_schedule_verification_of_single_port
        )

        state.flapping.clear_flap(("localhost", port.ifindex), "nobody", state, polldevs_dict["localhost"])

        mock_schedule_verification_of_single_port.assert_called_once()
        assert mock_schedule_verification_of_single_port.call_args[0][0] == port.ifindex

    def test_when_port_does_not_exist_it_should_not_schedule_verification(
        self,
        state_with_flapstats_and_portstate_event,
        polldevs_dict,
        monkeypatch,
    ):
        state = state_with_flapstats_and_portstate_event
        fake_ifindex = 999
        mock_schedule_verification_of_single_port = Mock()
        monkeypatch.setattr(
            LinkStateTask, "schedule_verification_of_single_port", mock_schedule_verification_of_single_port
        )

        state.flapping.clear_flap(("localhost", fake_ifindex), "nobody", state, polldevs_dict["localhost"])

        mock_schedule_verification_of_single_port.assert_not_called()


@pytest.fixture
def state_with_flapstats_and_portstate_event(state_with_flapstats) -> ZinoState:
    port: Port = next(iter(state_with_flapstats.devices.devices["localhost"].ports.values()))
    flapping_state = state_with_flapstats.flapping.interfaces[("localhost", port.ifindex)]
    flapping_state.hist_val = FLAP_THRESHOLD

    orig_event = state_with_flapstats.events.get_or_create_event("localhost", port.ifindex, PortStateEvent)
    orig_event.flapstate = FlapState.FLAPPING
    orig_event.flaps = 42
    orig_event.port = port.ifdescr
    orig_event.portstate = port.state
    orig_event.router = "localhost"
    orig_event.polladdr = "127.0.0.1"
    orig_event.priority = 500
    orig_event.ifindex = port.ifindex
    orig_event.descr = port.ifalias

    state_with_flapstats.events.commit(orig_event)
    return state_with_flapstats


class TestAgeSingleInterfaceFlappingState:
    @pytest.mark.asyncio
    async def test_it_should_decrease_hist_val(self, state_with_flapstats, polldevs_dict):
        port: Port = next(iter(state_with_flapstats.devices.devices["localhost"].ports.values()))
        flapping_state = state_with_flapstats.flapping.interfaces[("localhost", port.ifindex)]
        initial = flapping_state.hist_val

        await age_single_interface_flapping_state(
            flapping_state, ("localhost", port.ifindex), state=state_with_flapstats, polldevs=polldevs_dict
        )
        assert flapping_state.hist_val < initial

    @pytest.mark.asyncio
    async def test_when_flap_is_below_threshold_it_should_remove_flapping_state(
        self, mocked_out_poll_single_interface, state_with_flapstats, polldevs_dict
    ):
        port: Port = next(iter(state_with_flapstats.devices.devices["localhost"].ports.values()))
        flapping_state = state_with_flapstats.flapping.interfaces[("localhost", port.ifindex)]
        flapping_state.hist_val = FLAP_THRESHOLD

        await age_single_interface_flapping_state(
            flapping_state, ("localhost", port.ifindex), state=state_with_flapstats, polldevs=polldevs_dict
        )

        assert not state_with_flapstats.flapping.interfaces


class TestStabilizeFlappingState:
    @pytest.mark.asyncio
    async def test_when_no_event_exists_it_should_create_an_event(
        self, mocked_out_poll_single_interface, state_with_flapstats, polldevs_dict
    ):
        port: Port = next(iter(state_with_flapstats.devices.devices["localhost"].ports.values()))
        flapping_state = state_with_flapstats.flapping.interfaces[("localhost", port.ifindex)]
        flapping_state.hist_val = FLAP_THRESHOLD

        assert len(state_with_flapstats.events.events) == 0

        await stabilize_flapping_state(
            flapping_state, ("localhost", port.ifindex), state=state_with_flapstats, polldevs=polldevs_dict
        )

        assert len(state_with_flapstats.events.events) > 0

    @pytest.mark.asyncio
    async def test_when_a_matching_event_exists_it_should_set_its_flapstate_to_stable(
        self, mocked_out_poll_single_interface, state_with_flapstats, polldevs_dict
    ):
        port: Port = next(iter(state_with_flapstats.devices.devices["localhost"].ports.values()))
        flapping_state = state_with_flapstats.flapping.interfaces[("localhost", port.ifindex)]
        flapping_state.hist_val = FLAP_THRESHOLD

        orig_event = state_with_flapstats.events.get_or_create_event("localhost", port.ifindex, PortStateEvent)
        orig_event.flapstate = FlapState.FLAPPING
        orig_event.flaps = 42
        orig_event.port = port.ifdescr
        orig_event.portstate = port.state
        orig_event.router = "localhost"
        orig_event.polladdr = "127.0.0.1"
        orig_event.priority = 500
        orig_event.ifindex = port.ifindex
        orig_event.descr = port.ifalias

        state_with_flapstats.events.commit(orig_event)

        await stabilize_flapping_state(
            flapping_state, ("localhost", port.ifindex), state=state_with_flapstats, polldevs=polldevs_dict
        )

        updated_event = state_with_flapstats.events.get_or_create_event("localhost", port.ifindex, PortStateEvent)
        assert updated_event
        assert updated_event.flapstate == FlapState.STABLE

    @pytest.mark.asyncio
    async def test_when_a_matching_closed_event_exists_it_should_set_its_flapstate_to_stable(
        self, mocked_out_poll_single_interface, state_with_flapstats, polldevs_dict
    ):
        port: Port = next(iter(state_with_flapstats.devices.devices["localhost"].ports.values()))
        flapping_state = state_with_flapstats.flapping.interfaces[("localhost", port.ifindex)]
        flapping_state.hist_val = FLAP_THRESHOLD

        orig_event = state_with_flapstats.events.get_or_create_event("localhost", port.ifindex, PortStateEvent)
        orig_event.flapstate = FlapState.FLAPPING
        orig_event.flaps = 42
        orig_event.port = port.ifdescr
        orig_event.portstate = port.state
        orig_event.router = "localhost"
        orig_event.polladdr = "127.0.0.1"
        orig_event.priority = 500
        orig_event.ifindex = port.ifindex
        orig_event.descr = port.ifalias

        state_with_flapstats.events.commit(orig_event)
        orig_event.set_state(EventState.CLOSED)
        state_with_flapstats.events.commit(orig_event)

        await stabilize_flapping_state(
            flapping_state, ("localhost", port.ifindex), state=state_with_flapstats, polldevs=polldevs_dict
        )

        closed_event = state_with_flapstats.events.get_closed_event("localhost", port.ifindex, PortStateEvent)
        assert closed_event
        assert closed_event.flapstate == FlapState.STABLE

    @pytest.mark.asyncio
    async def test_when_port_is_unkown_it_should_still_log_the_change(
        self,
        mocked_out_poll_single_interface,
        state_with_flapstats,
        polldevs_dict,
        caplog,
    ):
        port: Port = next(iter(state_with_flapstats.devices.devices["localhost"].ports.values()))
        flapping_state = state_with_flapstats.flapping.interfaces[("localhost", port.ifindex)]
        flapping_state.hist_val = FLAP_THRESHOLD
        fake_ifindex = port.ifindex + 666

        with caplog.at_level(logging.INFO):
            await stabilize_flapping_state(
                flapping_state, ("localhost", fake_ifindex), state=state_with_flapstats, polldevs=polldevs_dict
            )

        assert f"{fake_ifindex} stopped flapping" in caplog.text


@pytest.mark.asyncio
async def test_age_flapping_states_should_age_all_flapping_states(monkeypatch, event_loop):
    future = event_loop.create_future()
    future.set_result(None)
    mock_ager = Mock(return_value=future)
    monkeypatch.setattr(flaps, "age_single_interface_flapping_state", mock_ager)

    state = ZinoState()
    state.flapping.first_flap(("localhost", 1))
    state.flapping.first_flap(("localhost", 2))

    await age_flapping_states(state, {})
    assert mock_ager.call_count == 2


@pytest.fixture
def state_with_flapstats(state_with_localhost_with_port) -> ZinoState:
    initial = FLAP_THRESHOLD * 2
    port: Port = next(iter(state_with_localhost_with_port.devices.devices["localhost"].ports.values()))
    last_change = now() - timedelta(minutes=1)
    flapping_state = FlappingState(
        hist_val=initial,
        first_flap=last_change - timedelta(minutes=10),
        last_flap=last_change,
        last_age=last_change,
    )
    flapstates = FlappingStates(interfaces={("localhost", port.ifindex): flapping_state})
    state_with_localhost_with_port.flapping = flapstates
    return state_with_localhost_with_port


@pytest.fixture
def polldevs_dict(polldevs_conf_with_single_router) -> dict[str, PollDevice]:
    return {"localhost": PollDevice(name="localhost", address=ipaddress.IPv4Address("127.0.0.1"))}


@pytest.fixture
def mocked_out_poll_single_interface(monkeypatch):
    """Monkey patches LinkStateTask.poll_single_interface to do essentially nothing"""
    future = Future()
    future.set_result(None)
    monkeypatch.setattr(LinkStateTask, "poll_single_interface", Mock(return_value=future))
    yield monkeypatch
