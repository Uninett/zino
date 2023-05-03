import logging
from datetime import datetime, timedelta

from zino import state
from zino.scheduler import get_scheduler
from zino.snmp import SNMP
from zino.statemodels import EventType
from zino.tasks.task import Task

_logger = logging.getLogger(__name__)


class ReachableTask(Task):
    EXTRA_JOBS_PREFIX = "delayed_reachable_job"
    EXTRA_JOBS_INTERVALS = [60, 120, 240, 480, 960]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._scheduler = get_scheduler()

    async def run(self):
        """Checks if device is reachable. Schedules extra jobs if not."""
        snmp = SNMP(self.device)
        result = await snmp.get("SNMPv2-MIB", "sysUpTime", 0)
        if not result:
            _logger.debug("Device %s is not reachable", self.device.name)
            event, created = state.events.get_or_create_event(self.device.name, None, EventType.REACHABILITY)
            if created:
                # TODO add attributes
                event.add_log(f"{self.device.name} no-response")
            if not self.extra_jobs_are_running():
                self.schedule_extra_jobs()
        else:
            _logger.debug("Device %s is reachable", self.device.name)
            event = state.events.get(self.device.name, None, EventType.REACHABILITY)
            if event:
                # TODO update event attributes
                event.add_log(f"{self.device.name} reachable")
            if self.extra_jobs_are_running():
                self.deschedule_extra_jobs()

    def schedule_extra_jobs(self):
        for interval in self.EXTRA_JOBS_INTERVALS:
            name = self.get_job_name_for_interval(interval)
            run_date = datetime.now() + timedelta(seconds=interval)
            self._scheduler.add_job(
                self.run,
                "date",
                run_date=run_date,
                name=name,
                id=name,
            )

    def deschedule_extra_jobs(self):
        for interval in self.EXTRA_JOBS_INTERVALS:
            name = self.get_job_name_for_interval(interval)
            self._scheduler.remove_job(name)

    def extra_jobs_are_running(self):
        for interval in self.EXTRA_JOBS_INTERVALS:
            job_name = self.get_job_name_for_interval(interval)
            if self._scheduler.get_job(job_name):
                return True
        return False

    def get_job_name_for_interval(self, interval):
        return f"{self.EXTRA_JOBS_PREFIX}_{interval}_{self.device.name}"
