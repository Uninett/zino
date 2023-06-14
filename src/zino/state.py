"""This module exists to hold global state for a Zino process"""

__all__ = ["polldevs", "devices"]

import logging
import pprint
from typing import Dict

from zino.config.models import PollDevice
from zino.events import Events

_log = logging.getLogger(__name__)
# Dictionary of configured devices
polldevs: Dict[str, PollDevice] = {}

# Dictionary of device state
devices = {}

# Dictionary of ongoing events
events = Events()


async def dump_state_to_log():
    _log.debug("Dumping state to log:\n%s", pprint.pformat(events.dict(exclude_none=True)))
