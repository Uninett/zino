"""Zino's own job scheduling, built on the reusable parts in :mod:`zino.polling`.

This module wires those parts to Zino's global state and tasks.  Code meant for reuse by other programs belongs in
:mod:`zino.polling` instead, so that importing it doesn't drag in Zino's state and tasks.
"""

import logging
import operator
from asyncio import AbstractEventLoop
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Sequence, Set, Tuple, Union

from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from zino import state
from zino.config.models import DEFAULT_INTERVAL_MINUTES, PollDevice
from zino.polling import PollfileWatcher, create_scheduler, diff_polldevs
from zino.statemodels import EventState
from zino.tasks import run_all_tasks
from zino.utils import log_time_spent

_log = logging.getLogger(__name__)
_scheduler = None


def get_scheduler(event_loop: Optional[AbstractEventLoop] = None) -> AsyncIOScheduler:
    """Returns the global scheduler, creating it on the first call.

    :param event_loop: The event loop to run jobs on.  Only used by the call that creates the scheduler.
    :return: The global scheduler
    """
    global _scheduler
    if _scheduler is None:
        _scheduler = create_scheduler(state.config.scheduler, event_loop)
    return _scheduler


@log_time_spent()
def load_polldevs(polldevs_conf: str) -> Tuple[Set, Set, Set, dict[str, str]]:
    """Loads pollfile into process state if it was changed since the last time it
    was loaded

    :returns: A tuple of (new_devices, deleted_devices, changed_devices, default_settings)
    """
    pollfile = _get_pollfile_watcher(polldevs_conf).read_if_changed()
    if pollfile is None:
        return set(), set(), set(), dict()
    devices, defaults = pollfile

    changes = diff_polldevs(state.polldevs, devices)
    new_devices, deleted_devices, changed_devices = set(changes.new), set(changes.deleted), set(changes.changed)

    if new_devices:
        _log.info("loaded new devices: %r", new_devices)
        init_state_for_devices((devices[d] for d in new_devices))
    if deleted_devices:
        _log.info("deleted devices: %r", deleted_devices)
    if changed_devices:
        _log.info("changed devices: %r", changed_devices)

    # Update polldevs
    state.polldevs.update(devices)
    for device in deleted_devices:
        del state.polldevs[device]

    # Update event/device state
    unmonitored_devices = set(state.state.devices.devices) - set(devices)
    close_events_for_devices(unmonitored_devices)
    delete_devicestate_for_devices(unmonitored_devices)

    return new_devices, deleted_devices, changed_devices, defaults


def _get_pollfile_watcher(polldevs_conf: Union[str, Path]) -> PollfileWatcher:
    """Returns the global pollfile watcher, replacing it if it watches a different file"""
    if state.pollfile_watcher is None or state.pollfile_watcher.path != Path(polldevs_conf):
        state.pollfile_watcher = PollfileWatcher(polldevs_conf)
    return state.pollfile_watcher


def init_state_for_devices(devices: Sequence[PollDevice]):
    """Initializes empty state structures for new devices, if none already exist"""
    for device in devices:
        state.state.addresses[device.address] = device.name
        state.state.devices.get(device.name)


async def load_and_schedule_polldevs(polldevs_conf: str):
    new_devices, deleted_devices, changed_devices, defaults = load_polldevs(polldevs_conf)
    deschedule_devices(deleted_devices | changed_devices)
    stagger_interval = defaults.get("interval", DEFAULT_INTERVAL_MINUTES)
    schedule_devices(new_devices | changed_devices, int(stagger_interval))


def schedule_devices(devices: Sequence[str], stagger_interval: int = DEFAULT_INTERVAL_MINUTES):
    devices = sorted((state.polldevs[name] for name in devices), key=operator.attrgetter("priority"), reverse=True)
    if not devices:
        return

    _log.debug("Scheduling %s devices", len(devices))

    scheduler = get_scheduler()

    # Spread poll jobs evenly across the entire default interval
    stagger_factor = (stagger_interval * 60) / len(devices)
    for index, device in enumerate(devices):
        first_run_time = datetime.now() + timedelta(seconds=index * stagger_factor)

        scheduler.add_job(
            func=run_all_tasks,
            trigger="interval",
            minutes=device.interval,
            args=(device, state.state, state.config),
            next_run_time=first_run_time,
            name=device.name,
            id=device.name,
        )


def deschedule_devices(devices: Sequence[str]):
    """De-schedules recurring jobs for the given devices"""
    scheduler = get_scheduler()
    for name in devices:
        try:
            scheduler.remove_job(job_id=name)
        except JobLookupError:
            _log.debug("Job for device %s could not be found", name)


def close_events_for_devices(devices: Sequence[str]):
    """Closes any non-closed events for given devices"""
    if not devices:
        return
    for event in state.state.events.events.values():
        if event.state is not EventState.CLOSED and event.router in devices:
            checked_out_event = state.state.events.checkout(event.id)
            checked_out_event.set_state(EventState.CLOSED)
            checked_out_event.add_log(f"Router {event.router} is no longer being monitored")
            state.state.events.commit(checked_out_event)


def delete_devicestate_for_devices(devices: Sequence[str]):
    """Deletes `DeviceState` for the given devices."""
    for device in devices:
        del state.state.devices.devices[device]
