import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from zino.config.models import PollDevice
from zino.jobs.job import Job
from zino.scheduler import get_scheduler
from zino.snmp import SNMP

_logger = logging.getLogger(__name__)


class ReachableJob(Job):
    EXTRA_JOBS_PREFIX = "delayed_reachable_job"
    EXTRA_JOBS_INTERVALS = [60, 120, 240, 480, 960]

    @classmethod
    async def run_job(cls, device: PollDevice):
        """Checks if device is reachable. Schedules extra jobs if not."""
        snmp = SNMP()
        result = await snmp.get("SNMPv2-MIB", "sysUpTime", 0)
        scheduler = get_scheduler()
        if not result:
            _logger.debug("Device %s is not reachable", device.name)
            if not cls.extra_jobs_are_running(scheduler):
                cls.schedule_extra_jobs(scheduler, device)
        else:
            _logger.debug("Device %s is reachable", device.name)
            if cls.extra_jobs_are_running(scheduler):
                cls.deschedule_extra_jobs(scheduler)

    @classmethod
    def schedule_extra_jobs(cls, scheduler: AsyncIOScheduler, device: PollDevice):
        for interval in cls.EXTRA_JOBS_INTERVALS:
            name = cls.get_job_name_for_interval(interval)
            # makes the job only run once
            end_date = datetime.now() + timedelta(seconds=interval)
            scheduler.add_job(
                cls.run_job,
                "interval",
                seconds=interval,
                args=(device,),
                name=name,
                id=name,
                end_date=end_date,
            )

    @classmethod
    def deschedule_extra_jobs(cls, scheduler: AsyncIOScheduler):
        for interval in cls.EXTRA_JOBS_INTERVALS:
            name = cls.get_job_name_for_interval(interval)
            scheduler.remove_job(name)

    @classmethod
    def extra_jobs_are_running(cls, scheduler: AsyncIOScheduler):
        for interval in cls.EXTRA_JOBS_INTERVALS:
            job_name = cls.get_job_name_for_interval(interval)
            if scheduler.get_job(job_name):
                return True
        return False

    @classmethod
    def get_job_name_for_interval(cls, interval):
        return f"{cls.EXTRA_JOBS_PREFIX}_{interval}"
