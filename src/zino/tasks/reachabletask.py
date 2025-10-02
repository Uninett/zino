import logging

from apscheduler.jobstores.base import JobLookupError

import zino.state
from zino.scheduler import get_scheduler
from zino.statemodels import ReachabilityEvent, ReachabilityState
from zino.tasks.errors import DeviceUnreachableError
from zino.tasks.task import Task

_logger = logging.getLogger(__name__)


class ReachableTask(Task):
    EXTRA_JOB_INTERVAL = 60

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._scheduler = get_scheduler()
        self._make_events_for_new_devices = zino.state.config.event.make_events_for_new_devices

    async def run(self):
        """Checks if device is reachable. Schedules extra reachability checks if not."""
        if self._extra_job_is_running():
            raise DeviceUnreachableError
        try:
            await self._get_uptime()
        except TimeoutError:
            event = self.state.events.get_or_create_event(self.device.name, None, ReachabilityEvent)
            if event.reachability != ReachabilityState.NORESPONSE:
                event.reachability = ReachabilityState.NORESPONSE
                if self.device_state.reachable_in_last_run is None and self._make_events_for_new_devices:
                    event.add_log(f"New device: {self.device.name} no-response")
                else:
                    event.add_log(f"{self.device.name} no-response")
            event.polladdr = self.device.address
            event.priority = self.device.priority
            self.state.events.commit(event)
            self.device_state.reachable_in_last_run = False
            self._schedule_extra_job()
            raise DeviceUnreachableError
        else:
            _logger.debug("Device %s is reachable", self.device.name)
            self._update_reachability_event_as_reachable()
            if self.device_state.reachable_in_last_run is None and self._make_events_for_new_devices:
                self._post_reachability_reachable_event_for_new_device()
            self.device_state.reachable_in_last_run = True

    async def _run_extra_job(self):
        try:
            # This runs outside a job context, so we need to ensure we clean up low-level SNMP resources
            with self.snmp:
                await self._get_uptime()
        except TimeoutError:
            return
        else:
            _logger.debug("Device %s is reachable", self.device.name)
            self._update_reachability_event_as_reachable()
            self._deschedule_extra_job()

    def _update_reachability_event_as_reachable(self):
        event = self.state.events.get(self.device.name, None, ReachabilityEvent)
        if event and event.reachability != ReachabilityState.REACHABLE:
            event = self.state.events.checkout(event.id)
            event.add_log(f"{self.device.name} reachable")
            event.reachability = ReachabilityState.REACHABLE
            self.state.events.commit(event)

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

    def _post_reachability_reachable_event_for_new_device(self):
        event = self.state.events.create_event(self.device.name, None, ReachabilityEvent)
        event.add_log(f"New device: {self.device.name} reachable")
        event.reachability = ReachabilityState.REACHABLE
        self.state.events.commit(event)
