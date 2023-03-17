import asyncio
import logging
from random import random

from zino.jobs.job import Job
from zino.config.models import PollDevice

_log = logging.getLogger(__name__)

class FauxPollJob(Job):

    async def run_job(cls, device: PollDevice):
        _log.debug("Fake polling %s in thread %s", device.name)
        await asyncio.sleep(random() * 5.0)
