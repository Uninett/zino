import asyncio

from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.schedulers.asyncio import AsyncIOScheduler


def init_scheduler() -> AsyncIOScheduler:
    executors = {
        "default": AsyncIOExecutor(),
    }
    job_defaults = {
        "max_instances": 1,  # Never allow same job to run simultaneously
    }
    return AsyncIOScheduler(event_loop=asyncio.get_event_loop(), executors=executors, job_defaults=job_defaults)
