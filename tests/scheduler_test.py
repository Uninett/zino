from unittest.mock import Mock, patch

import pytest

from zino import scheduler


class TestLoadPolldevs:
    @patch("zino.state.polldevs", dict())
    def test_should_return_all_new_devices_on_first_run(self, polldevs_conf):
        new_devices, deleted_devices = scheduler.load_polldevs(polldevs_conf)
        assert len(new_devices) > 0
        assert not deleted_devices

    @patch("zino.state.polldevs", dict())
    def test_should_return_deleted_devices_on_second_run(self, polldevs_conf, polldevs_conf_with_single_router):
        scheduler.load_polldevs(polldevs_conf)
        new_devices, deleted_devices = scheduler.load_polldevs(polldevs_conf_with_single_router)
        assert not new_devices
        assert len(deleted_devices) > 0


class TestScheduleNewDevices:
    @patch("zino.state.polldevs", dict())
    def test_should_schedule_jobs_for_new_devices(self, polldevs_conf, mocked_scheduler):
        new_devices, _ = scheduler.load_polldevs(polldevs_conf)
        assert len(new_devices) > 0

        scheduler.schedule_new_devices(new_devices)
        assert mocked_scheduler.add_job.called

    @patch("zino.state.polldevs", dict())
    def test_should_do_nothing_when_device_list_is_empty(self, mocked_scheduler):
        scheduler.schedule_new_devices([])
        assert not mocked_scheduler.add_job.called


def test_deschedule_deleted_devices_should_deschedule_jobs(mocked_scheduler):
    scheduler.deschedule_deleted_devices(["test-gw"])
    assert mocked_scheduler.remove_job.called


def test_scheduler_should_be_initialized_without_error():
    sched = scheduler.get_scheduler()
    assert sched


@pytest.fixture
def mocked_scheduler():
    with patch("zino.scheduler.get_scheduler") as get_scheduler:
        mock_scheduler = Mock()
        get_scheduler.return_value = mock_scheduler

        yield mock_scheduler
