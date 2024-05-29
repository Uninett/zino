from datetime import datetime, timedelta
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


def test_should_start_with_no_planned_maintenances(pms):
    assert len(pms) == 0


def test_pm_should_be_gettable_by_id(pms, active_pm):
    assert pms[active_pm.id] == active_pm


class TestGetPlannedMaintenances:
    def test_get_started_planned_maintenances(self, pms, active_pm, ended_pm, old_pm):
        pms.last_run = datetime.now() - timedelta(hours=1)
        recent_pm = pms.create_planned_maintenance(
            start_time=datetime.now() - timedelta(minutes=1),
            end_time=datetime.now() + timedelta(days=1),
            pm_class=DeviceMaintenance,
            match_type="str",
            match_expression="hello",
            match_device="device",
        )
        started_pms = pms.get_started_planned_maintenances(now=datetime.now())
        assert recent_pm in started_pms
        assert active_pm not in started_pms
        assert ended_pm not in started_pms
        assert old_pm not in started_pms

    def test_get_ended_planned_maintenances(self, pms, active_pm, ended_pm, old_pm):
        pms.last_run = datetime.now() - timedelta(hours=1)
        ended_pms = pms.get_ended_planned_maintenances(now=datetime.now())
        assert ended_pm in ended_pms
        assert old_pm not in ended_pms
        assert active_pm not in ended_pms

    def test_get_active_planned_maintenances(self, pms, active_pm, ended_pm, old_pm):
        active_pms = pms.get_active_planned_maintenances(datetime.now())
        assert active_pm in active_pms
        assert ended_pm not in active_pms
        assert old_pm not in active_pms

    def test_get_old_planned_maintenances(self, pms, active_pm, ended_pm, old_pm):
        old_pms = pms.get_old_planned_maintenances(now=datetime.now())
        assert old_pm in old_pms
        assert active_pm not in old_pms
        assert ended_pm not in old_pms


class TestClosePlannedMaintenance:
    def test_existing_pm_should_be_deleted(self, pms, old_pm):
        pms.close_planned_maintenance(old_pm.id, "test", "test")
        assert old_pm.id not in pms.planned_maintenances

    def test_should_not_raise_exception_if_no_matching_pm(self, pms, old_pm):
        assert pms.close_planned_maintenance(pms.get_next_available_pm_id(), "test", "test") is None

    def test_should_call_observers_after_closing_pm(self, pms, old_pm):
        observer = Mock()
        pms.add_pm_observer(observer.observe)
        pms.close_planned_maintenance(old_pm.id, "test", "test")
        assert observer.observe.called


class TestUpdatePmStates:
    def test_events_matching_active_device_pm_are_set_to_ignored(self, state, active_pm):
        device = state.devices.get("device")
        state.planned_maintenances.update_pm_states(state)
        reachability_event = state.events.get(device.name, None, ReachabilityEvent)
        assert reachability_event.state == EventState.IGNORED
        yellow_alarm_event = state.events.get(device.name, "yellow", AlarmEvent)
        assert yellow_alarm_event.state == EventState.IGNORED
        red_alarm_event = state.events.get(device.name, "red", AlarmEvent)
        assert red_alarm_event.state == EventState.IGNORED

    def test_events_matching_active_portstate_pm_are_set_to_ignored(self, state, active_portstate_pm):
        device = state.devices.get("device")
        port = Port(ifindex=1, ifdescr="port")
        device.ports[port.ifindex] = port
        state.planned_maintenances.update_pm_states(state)
        event = state.events.get(device.name, port.ifindex, PortStateEvent)
        assert event.state == EventState.IGNORED

    def test_events_affected_by_pm_get_opened_after_pm_ends(self, state, ended_pm):
        device = state.devices.get("device")

        # Create event and register it as affected by PM
        reachability_event = state.events.create_event(device.name, None, ReachabilityEvent)
        reachability_event.state == EventState.IGNORED
        state.events.commit(reachability_event)
        ended_pm.event_ids.append(reachability_event.id)

        state.planned_maintenances.update_pm_states(state)
        assert reachability_event.state == EventState.OPEN

    def test_old_pms_are_deleted(self, state, old_pm):
        assert old_pm.id in state.planned_maintenances.planned_maintenances
        state.planned_maintenances.update_pm_states(state)
        assert old_pm.id not in state.planned_maintenances.planned_maintenances

    def test_event_opened_after_pm_was_initiated_is_set_to_ignored(self, state, active_pm):
        device = state.devices.get("device")
        event = state.events.create_event(device.name, None, ReachabilityEvent)
        event.state = EventState.OPEN
        state.events.commit(event)
        # Set last run to be after start time so PM is not treated as if it just started
        state.planned_maintenances.last_run = active_pm.start_time + timedelta(hours=1)
        state.planned_maintenances.update_pm_states(state)
        assert state.events.checkout(event.id).state == EventState.IGNORED


@pytest.fixture
def pms():
    return PlannedMaintenances()


@pytest.fixture
def state(pms):
    state = ZinoState()
    state.planned_maintenances = pms
    return state


@pytest.fixture
def active_pm(pms):
    return pms.create_planned_maintenance(
        start_time=datetime.now() - timedelta(days=1),
        end_time=datetime.now() + timedelta(days=1),
        pm_class=DeviceMaintenance,
        match_type="exact",
        match_expression="device",
        match_device="device",
    )


@pytest.fixture
def active_portstate_pm(pms):
    return pms.create_planned_maintenance(
        start_time=datetime.now() - timedelta(days=1),
        end_time=datetime.now() + timedelta(days=1),
        pm_class=PortStateMaintenance,
        match_type="regexp",
        match_expression="port",
        match_device="device",
    )


@pytest.fixture
def ended_pm(pms):
    return pms.create_planned_maintenance(
        start_time=datetime.now() - timedelta(days=1),
        end_time=datetime.now() - timedelta(minutes=10),
        pm_class=DeviceMaintenance,
        match_type="exact",
        match_expression="device",
        match_device="device",
    )


@pytest.fixture
def old_pm(pms):
    return pms.create_planned_maintenance(
        start_time=datetime.now() - timedelta(days=100),
        end_time=datetime.now() - timedelta(days=99),
        pm_class=DeviceMaintenance,
        match_type="exact",
        match_expression="device",
        match_device="device",
    )
