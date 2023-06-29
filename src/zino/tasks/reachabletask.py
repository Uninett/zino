import logging

from apscheduler.jobstores.base import JobLookupError

from zino.scheduler import get_scheduler
from zino.snmp import SNMP
from zino.state import state
from zino.statemodels import EventState, ReachabilityEvent, ReachabilityState
from zino.tasks.task import Task

_logger = logging.getLogger(__name__)


class ReachableTask(Task):
    EXTRA_JOB_INTERVAL = 60

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._scheduler = get_scheduler()

    async def run(self):
        """Checks if device is reachable. Schedules extra reachability checks if not."""
        if self._extra_job_is_running():
            return
        result = await self._get_sysuptime()
        if not result:
            _logger.debug("Device %s is not reachable", self.device.name)
            event, created = state.events.get_or_create_event(self.device.name, None, ReachabilityEvent)
            if created:
                # TODO add attributes
                event.state = EventState.OPEN
                event.add_history("Change state to Open")
            if event.reachability != ReachabilityState.NORESPONSE:
                event.reachability = ReachabilityState.NORESPONSE
                event.add_log(f"{self.device.name} no-response")
            # TODO we need a mechanism to "commit" event changes, to trigger notifications to clients
            self._schedule_extra_job()
        else:
            _logger.debug("Device %s is reachable", self.device.name)
            self._update_reachability_event_as_reachable()

    async def _run_extra_job(self):
        result = await self._get_sysuptime()
        if result:
            _logger.debug("Device %s is reachable", self.device.name)
            self._update_reachability_event_as_reachable()
            self._deschedule_extra_job()

    async def _get_sysuptime(self):
        snmp = SNMP(self.device)
        result = await snmp.get("SNMPv2-MIB", "sysUpTime", 0)
        return result

    def _update_reachability_event_as_reachable(self):
        event = state.events.get(self.device.name, None, ReachabilityEvent)
        if event and event.reachability != ReachabilityState.REACHABLE:
            event.reachability = ReachabilityState.REACHABLE
            event.add_log(f"{self.device.name} reachable")
        # TODO we need a mechanism to "commit" event changes, to trigger notifications to clients

    def _schedule_extra_job(self):
        name = self._get_extra_job_name()
        self._scheduler.add_job(
            func=self._run_extra_job,
            trigger="interval",
            seconds=self.EXTRA_JOB_INTERVAL,
            name=name,
            id=name,
        )

    def _deschedule_extra_job(self):
        name = self._get_extra_job_name()
        try:
            self._scheduler.remove_job(job_id=name)
        except JobLookupError:
            pass

    def _extra_job_is_running(self):
        name = self._get_extra_job_name()
        if self._scheduler.get_job(job_id=name):
            return True
        else:
            return False

    def _get_extra_job_name(self):
        return f"reachabletask_{self.device.name}"
