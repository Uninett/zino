"""Reusable building blocks for daemons that poll the devices listed in a pollfile.

Nothing in here depends on Zino's global state, so other daemons can use it to schedule their own poll jobs.
"""

import logging
import operator
from asyncio import AbstractEventLoop
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Awaitable, Callable, Iterable, Mapping, Optional, Union

from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.util import iscoroutinefunction_partial

from zino.config.models import DEFAULT_INTERVAL_MINUTES, PollDevice, SchedulerConfiguration
from zino.config.polldevs import InvalidConfiguration, read_polldevs

_log = logging.getLogger(__name__)

PollJob = Callable[[PollDevice], Awaitable[None]]
"""A coroutine function that polls a single device"""


def create_scheduler(
    config: SchedulerConfiguration, event_loop: Optional[AbstractEventLoop] = None
) -> AsyncIOScheduler:
    """Creates a job scheduler that runs coroutine jobs on an asyncio event loop.

    Jobs never run as more than one instance at a time.

    :param config: The scheduler configuration to apply
    :param event_loop: The event loop to run jobs on.  If omitted, the scheduler uses the loop that is running when
        it is started, so it must then be started from inside a coroutine.
    :return: A new scheduler, not yet started
    """
    return AsyncIOScheduler(
        event_loop=event_loop,
        executors={"default": AsyncIOExecutor()},
        job_defaults={
            "max_instances": 1,
            "misfire_grace_time": config.misfire_grace_time,
        },
    )


class PollfileWatcher:
    """Re-reads a pollfile, but only when it has changed since the last successful read"""

    def __init__(self, path: Union[str, Path]) -> None:
        """
        :param path: The pollfile to watch
        """
        self._path = Path(path)
        self._mtime: Optional[float] = None

    @property
    def path(self) -> Path:
        """The pollfile being watched"""
        return self._path

    def read_if_changed(self) -> Optional[tuple[dict[str, PollDevice], dict[str, str]]]:
        """Reads the pollfile, if its modification time changed since the last successful read.

        A missing or invalid pollfile is logged as an error.  It does not count as a successful read, so it is
        retried, and logged again, on the next call.

        :return: The devices and the default settings of the pollfile, like :func:`read_polldevs`, or None if the
            pollfile is unchanged, missing or invalid
        """
        try:
            mtime = self._path.stat().st_mtime
        except OSError as error:
            _log.error(error)
            return None
        if mtime == self._mtime:
            return None

        try:
            devices, defaults = read_polldevs(self._path)
        except (InvalidConfiguration, OSError) as error:
            _log.error(error)
            return None

        self._mtime = mtime
        return devices, defaults


@dataclass(frozen=True)
class PolldevsChanges:
    """The names of devices that differ between two versions of a pollfile"""

    new: frozenset[str] = frozenset()
    deleted: frozenset[str] = frozenset()
    changed: frozenset[str] = frozenset()


def diff_polldevs(old: Mapping[str, PollDevice], new: Mapping[str, PollDevice]) -> PolldevsChanges:
    """Compares two versions of a pollfile's devices.

    A device counts as changed if any of its settings changed, including settings it inherits from the pollfile's
    defaults.

    :param old: The devices from the previous version, keyed by name
    :param new: The devices from the current version, keyed by name
    :return: The names of the new, deleted and changed devices
    """
    return PolldevsChanges(
        new=frozenset(new.keys() - old.keys()),
        deleted=frozenset(old.keys() - new.keys()),
        changed=frozenset(name for name in old.keys() & new.keys() if old[name] != new[name]),
    )


def schedule_device_jobs(
    devices: Iterable[PollDevice],
    job: PollJob,
    scheduler: AsyncIOScheduler,
    stagger_interval: int = DEFAULT_INTERVAL_MINUTES,
) -> None:
    """Schedules a recurring job for each device, at each device's own poll interval.

    The first runs are spread evenly across ``stagger_interval``, highest priority devices first, so that a large
    pollfile does not poll every device at once.  Each job's id and name is the device name.

    :param devices: The devices to schedule jobs for
    :param job: The coroutine function to run for each device.  It is called with the device as its only argument.
    :param scheduler: The scheduler to add the jobs to
    :param stagger_interval: The number of minutes to spread the first runs across
    :raises TypeError: If ``job`` is not a coroutine function, since the scheduler would run it in a worker thread
    """
    if not iscoroutinefunction_partial(job):
        raise TypeError(f"{job!r} is not a coroutine function")

    by_priority = sorted(devices, key=operator.attrgetter("priority"), reverse=True)
    if not by_priority:
        return

    _log.debug("Scheduling %s devices", len(by_priority))
    stagger_factor = (stagger_interval * 60) / len(by_priority)
    for index, device in enumerate(by_priority):
        first_run_time = datetime.now() + timedelta(seconds=index * stagger_factor)
        scheduler.add_job(
            func=job,
            trigger="interval",
            minutes=device.interval,
            args=(device,),
            next_run_time=first_run_time,
            name=device.name,
            id=device.name,
        )


def deschedule_device_jobs(names: Iterable[str], scheduler: AsyncIOScheduler) -> None:
    """Removes the recurring jobs of the given devices, ignoring devices that have no job.

    :param names: The names of the devices to remove jobs for
    :param scheduler: The scheduler to remove the jobs from
    """
    for name in names:
        try:
            scheduler.remove_job(job_id=name)
        except JobLookupError:
            _log.debug("Job for device %s could not be found", name)
