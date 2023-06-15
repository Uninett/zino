import asyncio
import logging
from random import random

from zino.tasks.task import Task

_log = logging.getLogger(__name__)


class FauxPollTask(Task):
    async def run(self):
        _log.debug("Fake polling %s in thread %s", self.device.name)
        await asyncio.sleep(random() * 5.0)
