import asyncio
import logging
from random import random

from zino.config.models import PollDevice
from zino.tasks.task import Task

_log = logging.getLogger(__name__)


class FauxPollTask(Task):
    async def run(cls, device: PollDevice):
        _log.debug("Fake polling %s in thread %s", device.name)
        await asyncio.sleep(random() * 5.0)
