import logging
from datetime import timedelta
from unittest.mock import Mock, patch

import pytest
from apscheduler.jobstores.base import JobLookupError

from zino import scheduler
from zino.state import ZinoState
from zino.time import now

YESTERDAY = last_run_time = now() - timedelta(days=1)


class TestLoadPolldevs:
    @patch("zino.state.polldevs", dict())
    @patch("zino.state.pollfile_mtime", None)
    @patch("zino.state.state", ZinoState())
    def test_should_return_all_new_devices_on_first_run(self, polldevs_conf):
        new_devices, deleted_devices, changed_devices, _ = scheduler.load_polldevs(polldevs_conf)
        assert len(new_devices) > 0
        assert not deleted_devices
        assert not changed_devices

    @patch("zino.state.polldevs", dict())
    @patch("zino.state.pollfile_mtime", None)
    @patch("zino.state.state", ZinoState())
    def test_should_return_defaults_on_first_run(self, polldevs_conf):
        _, _, _, defaults = scheduler.load_polldevs(polldevs_conf)
        assert len(defaults) > 0
        assert "interval" in defaults

    @patch("zino.state.polldevs", dict())
    @patch("zino.state.pollfile_mtime", None)
    @patch("zino.state.state", ZinoState())
    def test_should_return_deleted_devices_on_second_run(self, polldevs_conf, polldevs_conf_with_single_router):
        scheduler.load_polldevs(polldevs_conf)

        # This needs to be patched since the mtime of the two conf fixtures is the same
        with patch("zino.state.pollfile_mtime", YESTERDAY):
            new_devices, deleted_devices, changed_devices, _ = scheduler.load_polldevs(polldevs_conf_with_single_router)

        assert not new_devices
        assert len(deleted_devices) > 0
        assert not changed_devices

    @patch("zino.state.polldevs", dict())
    @patch("zino.state.pollfile_mtime", None)
    @patch("zino.state.state", ZinoState())
    def test__or_deleted_devices_on_invalid_configuration(self, invalid_polldevs_conf):
        new_devices, deleted_devices, changed_devices, _ = scheduler.load_polldevs(invalid_polldevs_conf)
        assert not new_devices
        assert not deleted_devices
        assert not changed_devices

    @patch("zino.state.polldevs", dict())
    @patch("zino.state.pollfile_mtime", None)
    @patch("zino.state.state", ZinoState())
    def test_should_log_error_on_invalid_configuration(self, caplog, invalid_polldevs_conf):
        with caplog.at_level(logging.ERROR):
            scheduler.load_polldevs(invalid_polldevs_conf)
        assert "'lalala' is not a valid configuration line" in caplog.text

    @patch("zino.state.polldevs", dict())
    @patch("zino.state.pollfile_mtime", None)
    @patch("zino.state.state", ZinoState())
    def test_should_return_changed_defaults(self, polldevs_conf, tmp_path):
        polldevs_with_changed_defaults = tmp_path.joinpath("changed-defaults-polldevs.cf")
        with open(polldevs_with_changed_defaults, "w") as conf:
            conf.write(
                """# polldevs test config
                default interval: 10
                default community: barfoo
                default domain: uninett.no
                default statistics: yes
                default hcounters: yes

                name: example-gw
                address: 10.0.42.1

                name: example-gw2
                address: 10.0.43.1"""  # Lack of a new-line here is intentional to test the parser
            )

        _, _, _, defaults = scheduler.load_polldevs(polldevs_conf)

        # This needs to be patched since the mtime of the two conf fixtures is the same
        with patch("zino.state.pollfile_mtime", YESTERDAY):
            _, _, _, changed_defaults = scheduler.load_polldevs(polldevs_with_changed_defaults)
        assert defaults != changed_defaults

    @patch("zino.state.polldevs", dict())
    @patch("zino.state.pollfile_mtime", None)
    @patch("zino.state.state", ZinoState())
    def test_should_return_changed_devices_on_changed_defaults(self, polldevs_conf, tmp_path):
        polldevs_with_changed_defaults = tmp_path.joinpath("changed-defaults-polldevs.cf")
        with open(polldevs_with_changed_defaults, "w") as conf:
            conf.write(
                """# polldevs test config
                default interval: 10
                default community: barfoo
                default domain: uninett.no
                default statistics: yes
                default hcounters: yes

                name: example-gw
                address: 10.0.42.1

                name: example-gw2
                address: 10.0.43.1"""  # Lack of a new-line here is intentional to test the parser
            )

        scheduler.load_polldevs(polldevs_conf)

        # This needs to be patched since the mtime of the two conf fixtures is the same
        with patch("zino.state.pollfile_mtime", YESTERDAY):
            new_devices, deleted_devices, changed_devices, _ = scheduler.load_polldevs(polldevs_with_changed_defaults)

        assert not new_devices
        assert not deleted_devices
        assert changed_devices

    @patch("zino.state.polldevs", dict())
    @patch("zino.state.pollfile_mtime", None)
    @patch("zino.state.state", ZinoState())
    def test_should_return_changed_devices_on_changed_interval(self, polldevs_conf, tmp_path):
        polldevs_with_changed_defaults = tmp_path.joinpath("changed-interval-polldevs.cf")
        with open(polldevs_with_changed_defaults, "w") as conf:
            conf.write(
                """# polldevs test config
                default interval: 5
                default community: foobar
                default domain: uninett.no
                default statistics: yes
                default hcounters: yes

                name: example-gw
                address: 10.0.42.1
                interval: 10

                name: example-gw2
                address: 10.0.43.1"""  # Lack of a new-line here is intentional to test the parser
            )

        scheduler.load_polldevs(polldevs_conf)

        # This needs to be patched since the mtime of the two conf fixtures is the same
        with patch("zino.state.pollfile_mtime", YESTERDAY):
            new_devices, deleted_devices, changed_devices, _ = scheduler.load_polldevs(polldevs_with_changed_defaults)

        assert not new_devices
        assert not deleted_devices
        assert changed_devices

    @patch("zino.state.polldevs", dict())
    @patch("zino.state.pollfile_mtime", None)
    @patch("zino.state.state", ZinoState())
    def test_should_return_no_new_or_deleted_devices_on_unchanged_configuration(self, polldevs_conf):
        scheduler.load_polldevs(polldevs_conf)
        new_devices, deleted_devices, _, _ = scheduler.load_polldevs(polldevs_conf)
        assert not new_devices
        assert not deleted_devices

    @patch("zino.state.polldevs", dict())
    @patch("zino.state.pollfile_mtime", None)
    @patch("zino.state.state", ZinoState())
    def test_should_return_no_new_or_deleted_devices_on_non_existent_pollfile(self, tmp_path):
        new_devices, deleted_devices, _, _ = scheduler.load_polldevs(tmp_path / "non-existent-polldev.cf")
        assert not new_devices
        assert not deleted_devices

    @patch("zino.state.polldevs", dict())
    @patch("zino.state.pollfile_mtime", None)
    @patch("zino.state.state", ZinoState())
    def test_should_log_error_on_non_existent_pollfile(self, caplog, tmp_path):
        with caplog.at_level(logging.ERROR):
            scheduler.load_polldevs(tmp_path / "non-existent-polldev.cf")
        assert "No such file or directory" in caplog.text


class TestScheduleNewDevices:
    @patch("zino.state.polldevs", dict())
    @patch("zino.state.pollfile_mtime", None)
    @patch("zino.state.state", ZinoState())
    def test_should_schedule_jobs_for_new_devices(self, polldevs_conf, mocked_scheduler):
        new_devices, _, _, _ = scheduler.load_polldevs(polldevs_conf)
        assert len(new_devices) > 0

        scheduler.schedule_devices(new_devices)
        assert mocked_scheduler.add_job.called

    @patch("zino.state.polldevs", dict())
    def test_should_do_nothing_when_device_list_is_empty(self, mocked_scheduler):
        scheduler.schedule_devices([])
        assert not mocked_scheduler.add_job.called


def test_deschedule_deleted_devices_should_deschedule_jobs(mocked_scheduler):
    scheduler.deschedule_devices(["test-gw"])
    assert mocked_scheduler.remove_job.called


def test_deschedule_deleted_devices_should_not_fail_on_not_found_job(mocked_scheduler_raising_error, caplog):
    with caplog.at_level(logging.DEBUG):
        scheduler.deschedule_devices(["test-gw"])
    assert mocked_scheduler_raising_error.remove_job.called
    assert "Job for device test-gw could not be found" in caplog.text


def test_scheduler_should_be_initialized_without_error():
    sched = scheduler.get_scheduler()
    assert sched


@pytest.fixture
def mocked_scheduler():
    with patch("zino.scheduler.get_scheduler") as get_scheduler:
        mock_scheduler = Mock()
        get_scheduler.return_value = mock_scheduler

        yield mock_scheduler


@pytest.fixture
def mocked_scheduler_raising_error():
    with patch("zino.scheduler.get_scheduler") as get_scheduler:
        mock_scheduler = Mock()
        mock_scheduler.remove_job.side_effect = Mock(side_effect=JobLookupError(job_id="fake id"))
        get_scheduler.return_value = mock_scheduler

        yield mock_scheduler
