import asyncio
import logging
import os
from datetime import datetime

import pytest

from zino.config.models import PollDevice, SchedulerConfiguration
from zino.polling import PolldevsChanges, PollfileWatcher, create_scheduler, diff_polldevs


class TestCreateScheduler:
    async def test_when_config_sets_misfire_grace_time_then_jobs_should_get_it(self, running_scheduler):
        job = running_scheduler.add_job(noop_job, trigger="interval", minutes=5)

        assert job.misfire_grace_time == MISFIRE_GRACE_TIME

    async def test_when_job_is_added_then_it_should_be_limited_to_one_instance(self, running_scheduler):
        job = running_scheduler.add_job(noop_job, trigger="interval", minutes=5)

        assert job.max_instances == 1

    def test_when_event_loop_is_given_then_jobs_should_run_on_it_even_if_started_before_it_runs(self):
        loop = asyncio.new_event_loop()
        scheduler = create_scheduler(SchedulerConfiguration(), event_loop=loop)
        loops_seen = []
        scheduler.add_job(record_running_loop, args=(loops_seen,), next_run_time=datetime.now())

        scheduler.start()
        try:
            loop.run_until_complete(wait_until(lambda: loops_seen))
        finally:
            scheduler.shutdown(wait=False)
            loop.run_until_complete(asyncio.sleep(0))
            loop.close()

        assert loops_seen == [loop]

    async def test_when_no_event_loop_is_given_then_jobs_should_run_on_the_loop_it_was_started_from(self):
        scheduler = create_scheduler(SchedulerConfiguration())
        loops_seen = []
        scheduler.add_job(record_running_loop, args=(loops_seen,), next_run_time=datetime.now())

        scheduler.start()
        try:
            await wait_until(lambda: loops_seen)
        finally:
            scheduler.shutdown(wait=False)

        assert loops_seen == [asyncio.get_running_loop()]


class TestPollfileWatcher:
    def test_when_read_for_the_first_time_then_it_should_return_devices_and_defaults(self, polldevs_conf):
        watcher = PollfileWatcher(polldevs_conf)

        devices, defaults = watcher.read_if_changed()

        assert set(devices) == {"example-gw", "example-gw2"}
        assert defaults["interval"] == "5"

    def test_when_pollfile_is_unchanged_then_it_should_return_none(self, polldevs_conf):
        watcher = PollfileWatcher(polldevs_conf)
        watcher.read_if_changed()

        assert watcher.read_if_changed() is None

    def test_when_pollfile_mtime_changes_then_it_should_read_it_again(self, polldevs_conf):
        watcher = PollfileWatcher(polldevs_conf)
        watcher.read_if_changed()
        touch_later(polldevs_conf)

        devices, _ = watcher.read_if_changed()

        assert set(devices) == {"example-gw", "example-gw2"}

    def test_when_pollfile_is_missing_then_it_should_log_an_error_and_return_none(self, tmp_path, caplog):
        watcher = PollfileWatcher(tmp_path / "missing.cf")

        with caplog.at_level(logging.ERROR):
            assert watcher.read_if_changed() is None

        assert "No such file or directory" in caplog.text

    def test_when_pollfile_stays_invalid_then_every_read_should_log_an_error(self, invalid_polldevs_conf, caplog):
        watcher = PollfileWatcher(invalid_polldevs_conf)

        with caplog.at_level(logging.ERROR):
            assert watcher.read_if_changed() is None
            assert watcher.read_if_changed() is None

        assert caplog.text.count("'lalala' is not a valid configuration line") == 2


class TestDiffPolldevs:
    def test_when_device_is_only_in_new_then_it_should_be_new(self):
        changes = diff_polldevs({}, {"a": make_device("a")})

        assert changes == PolldevsChanges(new=frozenset({"a"}))

    def test_when_device_is_only_in_old_then_it_should_be_deleted(self):
        changes = diff_polldevs({"a": make_device("a")}, {})

        assert changes == PolldevsChanges(deleted=frozenset({"a"}))

    def test_when_device_settings_differ_then_it_should_be_changed(self):
        changes = diff_polldevs({"a": make_device("a")}, {"a": make_device("a", interval=10)})

        assert changes == PolldevsChanges(changed=frozenset({"a"}))

    def test_when_device_settings_are_equal_then_there_should_be_no_changes(self):
        changes = diff_polldevs({"a": make_device("a")}, {"a": make_device("a")})

        assert changes == PolldevsChanges()


MISFIRE_GRACE_TIME = 42


@pytest.fixture
async def running_scheduler():
    scheduler = create_scheduler(SchedulerConfiguration(misfire_grace_time=MISFIRE_GRACE_TIME))
    scheduler.start()
    yield scheduler
    scheduler.shutdown(wait=False)


async def noop_job():
    pass


async def record_running_loop(loops_seen: list):
    loops_seen.append(asyncio.get_running_loop())


async def wait_until(condition, timeout: float = 2.0):
    async with asyncio.timeout(timeout):
        while not condition():
            await asyncio.sleep(0.01)


def make_device(name: str, **settings) -> PollDevice:
    return PollDevice(name=name, address="127.0.0.1", **settings)


def touch_later(path):
    """Moves the file's modification time forward, so it differs even on file systems with coarse timestamps"""
    mtime = os.stat(path).st_mtime + 10
    os.utime(path, (mtime, mtime))
