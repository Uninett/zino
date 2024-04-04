from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest

from zino.planned_maintenance import PlannedMaintenances
from zino.state import ZinoState
from zino.statemodels import AlarmEvent, EventState, ReachabilityEvent


class TestGetPlannedMaintenances:
    def test_get_started_planned_maintenances(self, pms, active_pm, ended_pm, old_pm):
        started_pms = pms.get_started_planned_maintenances(now=datetime.now())
        assert active_pm in started_pms
        assert ended_pm not in started_pms
        assert old_pm not in started_pms

    def test_get_started_planned_maintenances_with_last_run(self, pms, active_pm, ended_pm, old_pm):
        pms.last_run = datetime.now() - timedelta(hours=1)
        recent_pm = pms.create_planned_maintenance(
            start_time=datetime.now() - timedelta(minutes=1),
            end_time=datetime.now() + timedelta(days=1),
            type="device",
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
        ended_pms = pms.get_ended_planned_maintenances(now=datetime.now())
        assert ended_pm in ended_pms
        assert old_pm in ended_pms
        assert active_pm not in ended_pms

    def test_get_ended_planned_maintenances_with_last_run(self, pms, active_pm, ended_pm, old_pm):
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
        assert pms.close_planned_maintenance(pms.last_pm_id + 1, "test", "test") is None

    def test_should_call_observers_after_closing_pm(self, pms, old_pm):
        observer = Mock()
        pms.add_pm_observer(observer.observe)
        pms.close_planned_maintenance(old_pm.id, "test", "test")
        assert observer.observe.called


class TestPeriodic:
    def test_events_matching_device_pm_are_set_in_ignore(self, state, active_pm):
        device = state.devices.get("device")
        state.planned_maintenances.periodic(state)
        reachability_event = state.events.get(device.name, None, ReachabilityEvent)
        assert reachability_event.state == EventState.IGNORED
        yellow_alarm_event = state.events.get(device.name, "yellow", AlarmEvent)
        assert yellow_alarm_event.state == EventState.IGNORED
        red_alarm_event = state.events.get(device.name, "red", AlarmEvent)
        assert red_alarm_event.state == EventState.IGNORED


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
        type="device",
        match_type="exact",
        match_expression="device",
        match_device="device",
    )


@pytest.fixture
def ended_pm(pms):
    return pms.create_planned_maintenance(
        start_time=datetime.now() - timedelta(days=1),
        end_time=datetime.now() - timedelta(minutes=10),
        type="device",
        match_type="str",
        match_expression="hello",
        match_device="device",
    )


@pytest.fixture
def old_pm(pms):
    return pms.create_planned_maintenance(
        start_time=datetime.now() - timedelta(days=100),
        end_time=datetime.now() - timedelta(days=99),
        type="device",
        match_type="str",
        match_expression="hello",
        match_device="device",
    )
