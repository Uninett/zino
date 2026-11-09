"""Reusable building blocks for daemons that poll the devices listed in a pollfile.

Nothing in here depends on Zino's global state, so other daemons can use it to schedule their own poll jobs.
"""

import logging
from asyncio import AbstractEventLoop
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional, Union

from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from zino.config.models import PollDevice, SchedulerConfiguration
from zino.config.polldevs import InvalidConfiguration, read_polldevs

_log = logging.getLogger(__name__)


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
