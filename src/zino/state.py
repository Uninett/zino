"""This module exists to hold global state for a Zino process"""

__all__ = ["polldevs", "devices"]

from typing import Dict

from zino.config.models import PollDevice
from zino.events import Events

# Dictionary of configured devices
polldevs: Dict[str, PollDevice] = {}

# Dictionary of device state
devices = {}

# Dictionary of ongoing events
events = Events()
