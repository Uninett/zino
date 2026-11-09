import asyncio
from datetime import datetime

import pytest

from zino.config.models import SchedulerConfiguration
from zino.polling import create_scheduler


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
