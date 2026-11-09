"""Reusable building blocks for daemons that poll the devices listed in a pollfile.

Nothing in here depends on Zino's global state, so other daemons can use it to schedule their own poll jobs.
"""

from asyncio import AbstractEventLoop
from typing import Optional

from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from zino.config.models import SchedulerConfiguration


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
