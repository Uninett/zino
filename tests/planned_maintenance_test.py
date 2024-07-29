from datetime import timedelta
from unittest.mock import Mock

import pytest

from zino.planned_maintenance import PlannedMaintenances
from zino.state import ZinoState
from zino.statemodels import (
    AlarmEvent,
    DeviceMaintenance,
    EventState,
    Port,
    PortStateEvent,
    PortStateMaintenance,
    ReachabilityEvent,
)
from zino.time import now


def test_should_start_with_no_planned_maintenances(pms):
    assert len(pms) == 0


def test_pm_should_be_gettable_by_id(pms, active_pm):
    assert pms[active_pm.id] == active_pm


class TestGetStartedPlannedMaintenances:
    def test_should_return_pms_that_started_since_last_run(self, pms, recent_pm):
        pms.last_run = now() - timedelta(hours=1)
        started_pms = pms.get_started_planned_maintenances(now=now())
        assert recent_pm in started_pms

    def test_should_not_return_pms_that_started_before_last_run(self, pms, active_pm):
        pms.last_run = now() - timedelta(hours=1)
        started_pms = pms.get_started_planned_maintenances(now=now())
        assert active_pm not in started_pms

    def test_should_not_return_pms_that_have_not_started_yet(self, pms, not_started_pm):
        pms.last_run = now() - timedelta(hours=1)
        started_pms = pms.get_started_planned_maintenances(now=now())
        assert not_started_pm not in started_pms


class TestGetEndedPlannedMaintenances:
    def test_should_return_pms_that_ended_after_last_run(self, pms, active_pm, ended_pm, old_pm):
        pms.last_run = now() - timedelta(hours=1)
        ended_pms = pms.get_ended_planned_maintenances(now=now())
        assert ended_pm in ended_pms

    def test_should_not_return_pms_that_ended_before_last_run(self, pms, old_pm):
        pms.last_run = now() - timedelta(hours=1)
        ended_pms = pms.get_ended_planned_maintenances(now=now())
        assert old_pm not in ended_pms

    def test_should_not_return_pms_that_have_not_ended(self, pms, active_pm):
        pms.last_run = now() - timedelta(hours=1)
        ended_pms = pms.get_ended_planned_maintenances(now=now())
        assert active_pm not in ended_pms


class TestGetActivePlannedMaintenances:
    def test_should_return_active_pms(self, pms, active_pm):
        active_pms = pms.get_active_planned_maintenances(now())
        assert active_pm in active_pms

    def test_should_not_return_ended_pms(self, pms, ended_pm):
        active_pms = pms.get_active_planned_maintenances(now())
        assert ended_pm not in active_pms

    def test_should_not_return_pms_that_have_not_started_yet(self, pms, not_started_pm):
        active_pms = pms.get_active_planned_maintenances(now())
        assert not_started_pm not in active_pms


class TestGetOldPlannedMaintenances:
    def test_should_return_old_pms(self, pms, old_pm):
        old_pms = pms.get_old_planned_maintenances(now=now())
        assert old_pm in old_pms

    def test_should_not_return_pms_that_have_not_ended_yet(self, pms, active_pm):
        old_pms = pms.get_old_planned_maintenances(now=now())
        assert active_pm not in old_pms

    def test_should_not_return_pms_that_ended_since_last_run(self, pms, ended_pm):
        old_pms = pms.get_old_planned_maintenances(now=now())
        assert ended_pm not in old_pms


class TestClosePlannedMaintenance:
    def test_existing_pm_should_be_deleted(self, pms, old_pm):
        pms.close_planned_maintenance(old_pm.id, "test", "test")
        assert old_pm.id not in pms.planned_maintenances

    def test_when_there_are_no_matching_pms_it_should_not_raise_exception(self, pms, old_pm):
        assert pms.close_planned_maintenance(pms.get_next_available_pm_id(), "test", "test") is None

    def test_should_call_observers_after_closing_pm(self, pms, old_pm):
        observer = Mock()
        pms.add_pm_observer(observer.observe)
        pms.close_planned_maintenance(old_pm.id, "test", "test")
        assert observer.observe.called


class TestUpdatePmStates:
    def test_events_matching_active_device_pm_should_be_set_to_ignored(self, state, active_pm):
        device = state.devices.get("device")
        state.planned_maintenances.update_pm_states(state)
        reachability_event = state.events.get(device.name, None, ReachabilityEvent)
        assert reachability_event.state == EventState.IGNORED
        yellow_alarm_event = state.events.get(device.name, "yellow", AlarmEvent)
        assert yellow_alarm_event.state == EventState.IGNORED
        red_alarm_event = state.events.get(device.name, "red", AlarmEvent)
        assert red_alarm_event.state == EventState.IGNORED

    def test_events_matching_active_portstate_pm_should_be_set_to_ignored(self, state, active_portstate_pm):
        device = state.devices.get("device")
        port = Port(ifindex=1, ifdescr="port")
        device.ports[port.ifindex] = port
        state.planned_maintenances.update_pm_states(state)
        event = state.events.get(device.name, port.ifindex, PortStateEvent)
        assert event.state == EventState.IGNORED

    def test_when_pm_ends_its_affected_events_should_be_opened(self, state, ended_pm):
        device = state.devices.get("device")

        # Create event and register it as affected by PM
        reachability_event = state.events.create_event(device.name, None, ReachabilityEvent)
        reachability_event.state = EventState.IGNORED
        state.events.commit(reachability_event)
        ended_pm.event_ids.append(reachability_event.id)

        state.planned_maintenances.update_pm_states(state)
        assert state.events.checkout(reachability_event.id).state == EventState.OPEN

    def test_old_pms_should_be_deleted(self, state, old_pm):
        assert old_pm.id in state.planned_maintenances.planned_maintenances
        state.planned_maintenances.update_pm_states(state)
        assert old_pm.id not in state.planned_maintenances.planned_maintenances

    def test_event_opened_after_pm_was_initiated_should_be_set_to_ignored(self, state, active_pm):
        device = state.devices.get("device")
        event = state.events.create_event(device.name, None, ReachabilityEvent)
        event.state = EventState.OPEN
        state.events.commit(event)
        # Set last run to be after start time so PM is not treated as if it just started
        state.planned_maintenances.last_run = active_pm.start_time + timedelta(hours=1)
        state.planned_maintenances.update_pm_states(state)
        assert state.events.checkout(event.id).state == EventState.IGNORED


def test_pms_should_be_parsed_as_correct_subclass_when_read_from_file(tmp_path, state, active_portstate_pm, active_pm):
    dumpfile = tmp_path / "dump.json"
    state.dump_state_to_file(dumpfile)
    read_state = ZinoState.load_state_from_file(str(dumpfile))
    read_device_pm = read_state.planned_maintenances[active_pm.id]
    read_portstate_pm = read_state.planned_maintenances[active_portstate_pm.id]
    assert isinstance(read_device_pm, DeviceMaintenance)
    assert isinstance(read_portstate_pm, PortStateMaintenance)


def test_model_dump_of_pm_should_use_aliases(state, active_portstate_pm, active_pm):
    state_dump = state.model_dump_json(exclude_none=True, indent=2, by_alias=True)
    assert "starttime" in state_dump
    assert "endtime" in state_dump
    assert "match_dev" in state_dump
    assert "match_expr" in state_dump


@pytest.fixture
def pms():
    return PlannedMaintenances()


@pytest.fixture
def state(pms):
    state = ZinoState()
    state.planned_maintenances = pms
    return state


@pytest.fixture
def not_started_pm(pms):
    return pms.create_planned_maintenance(
        start_time=now() + timedelta(days=1),
        end_time=now() + timedelta(days=2),
        pm_class=DeviceMaintenance,
        match_type="exact",
        match_expression="device",
        match_device="device",
    )


@pytest.fixture
def recent_pm(pms):
    return pms.create_planned_maintenance(
        start_time=now() - timedelta(minutes=1),
        end_time=now() + timedelta(days=1),
        pm_class=DeviceMaintenance,
        match_type="str",
        match_expression="hello",
        match_device="device",
    )


@pytest.fixture
def active_pm(pms):
    return pms.create_planned_maintenance(
        start_time=now() - timedelta(days=1),
        end_time=now() + timedelta(days=1),
        pm_class=DeviceMaintenance,
        match_type="exact",
        match_expression="device",
        match_device="device",
    )


@pytest.fixture
def active_portstate_pm(pms):
    return pms.create_planned_maintenance(
        start_time=now() - timedelta(days=1),
        end_time=now() + timedelta(days=1),
        pm_class=PortStateMaintenance,
        match_type="regexp",
        match_expression="port",
        match_device="device",
    )


@pytest.fixture
def ended_pm(pms):
    return pms.create_planned_maintenance(
        start_time=now() - timedelta(days=1),
        end_time=now() - timedelta(minutes=10),
        pm_class=DeviceMaintenance,
        match_type="exact",
        match_expression="device",
        match_device="device",
    )


@pytest.fixture
def old_pm(pms):
    return pms.create_planned_maintenance(
        start_time=now() - timedelta(days=100),
        end_time=now() - timedelta(days=99),
        pm_class=DeviceMaintenance,
        match_type="exact",
        match_expression="device",
        match_device="device",
    )
