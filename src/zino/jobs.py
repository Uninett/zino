import asyncio
import logging
from random import random

from zino.config.models import PollDevice

_log = logging.getLogger(__name__)


async def faux_poll(device: PollDevice):
    _log.debug("Fake polling %s in thread %s", device.name)
    await asyncio.sleep(random() * 5.0)
