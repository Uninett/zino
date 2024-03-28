from datetime import datetime, timedelta

import pytest

from zino.planned_maintenance import PlannedMaintenances


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
        active_pms = pms.get_active_planned_maintenances()
        assert active_pm in active_pms
        assert ended_pm not in active_pms
        assert old_pm not in active_pms

    def test_get_old_planned_maintenances(self, pms, active_pm, ended_pm, old_pm):
        old_pms = pms.get_old_planned_maintenances(now=datetime.now())
        assert old_pm in old_pms
        assert active_pm not in old_pms
        assert ended_pm not in old_pms


@pytest.fixture
def pms():
    return PlannedMaintenances()


@pytest.fixture
def active_pm(pms):
    return pms.create_planned_maintenance(
        start_time=datetime.now() - timedelta(days=1),
        end_time=datetime.now() + timedelta(days=1),
        type="device",
        match_type="str",
        match_expression="hello",
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
