import asyncio
import logging
from random import random

from zino.config.models import PollDevice
from zino.jobs.job import Job

_log = logging.getLogger(__name__)


class FauxPollJob(Job):
    @classmethod
    async def run_job(cls, device: PollDevice):
        _log.debug("Fake polling %s in thread %s", device.name)
        await asyncio.sleep(random() * 5.0)
