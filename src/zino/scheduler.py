import asyncio
import logging
import operator
from datetime import datetime, timedelta
from typing import Sequence, Set, Tuple

from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from zino import state
from zino.config.models import DEFAULT_INTERVAL_MINUTES, PollDevice
from zino.config.polldevs import InvalidConfiguration, read_polldevs
from zino.tasks import run_all_tasks
from zino.utils import log_time_spent

_log = logging.getLogger(__name__)
_scheduler = None


def get_scheduler() -> AsyncIOScheduler:
    """Returns the global scheduler.

    Creates the global scheduler on the first call.
    """
    global _scheduler
    if _scheduler is None:
        executors = {
            "default": AsyncIOExecutor(),
        }
        job_defaults = {
            "max_instances": 1,  # Never allow same job to run simultaneously
        }
        _scheduler = AsyncIOScheduler(
            event_loop=asyncio.get_event_loop(),
            executors=executors,
            job_defaults=job_defaults,
        )
    return _scheduler


@log_time_spent()
def load_polldevs(polldevs_conf: str) -> Tuple[Set, Set]:
    """Loads pollfile into process state.

    :returns: A tuple of (new_devices, deleted_devices)
    """
    try:
        devices = {d.name: d for d in read_polldevs(polldevs_conf)}
    except InvalidConfiguration as error:
        _log.error(error)
        return set(), set()

    new_devices = set(devices) - set(state.polldevs)
    deleted_devices = set(state.polldevs) - set(devices)
    if new_devices:
        _log.info("loaded new devices: %r", new_devices)
        init_state_for_devices((devices[d] for d in new_devices))
    if deleted_devices:
        _log.info("deleted devices: %r", deleted_devices)

    state.polldevs.update(devices)
    for device in deleted_devices:
        del state.polldevs[device]

    return new_devices, deleted_devices


def init_state_for_devices(devices: Sequence[PollDevice]):
    """Initializes empty state structures for new devices, if none already exist"""
    for device in devices:
        state.state.addresses[device.address] = device.name
        state.state.devices.get(device.name)


async def load_and_schedule_polldevs(polldevs_conf: str):
    new_devices, deleted_devices = load_polldevs(polldevs_conf)
    schedule_new_devices(new_devices)
    deschedule_deleted_devices(deleted_devices)


def schedule_new_devices(new_devices: Sequence[str]):
    devices = sorted((state.polldevs[name] for name in new_devices), key=operator.attrgetter("priority"), reverse=True)
    if not devices:
        return

    _log.debug("Scheduling %s new devices", len(devices))

    scheduler = get_scheduler()

    # Spread poll jobs evenly across the entire default interval
    stagger_factor = (DEFAULT_INTERVAL_MINUTES * 60) / len(devices)
    for index, device in enumerate(devices):
        first_run_time = datetime.now() + timedelta(seconds=index * stagger_factor)

        scheduler.add_job(
            func=run_all_tasks,
            trigger="interval",
            minutes=device.interval,
            args=(device, state.state),
            next_run_time=first_run_time,
            name=device.name,
            id=device.name,
        )


def deschedule_deleted_devices(deleted_devices: Sequence[str]):
    """De-schedules recurring jobs for the deleted devices"""
    scheduler = get_scheduler()
    for name in deleted_devices:
        try:
            scheduler.remove_job(job_id=name)
        except JobLookupError:
            _log.debug("Job for device %s could not be found", name)
