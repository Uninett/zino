"""This module exists to hold global state for a Zino process"""

__all__ = ["polldevs", "ZinoState"]

import json
import logging
from typing import Dict, Optional

from pydantic import BaseModel, Field

from zino.config.models import PollDevice
from zino.events import Events
from zino.statemodels import DeviceStates

_log = logging.getLogger(__name__)
STATE_FILENAME = "zino-state.json"

# Dictionary of configured devices
polldevs: Dict[str, PollDevice] = {}

# Global (sic) state
state: "ZinoState" = None


class ZinoState(BaseModel):
    """Holds all state that Zino needs to persist between runtimes"""

    devices: DeviceStates = Field(default_factory=DeviceStates)
    events: Events = Field(default_factory=Events)

    def dump_state_to_file(self, filename: str = STATE_FILENAME):
        """Dumps the full state to a file in JSON format"""
        _log.debug("dumping state to %s", filename)
        with open(filename, "w") as statefile:
            statefile.write(self.model_dump_json(exclude_none=True, indent=2))

    @classmethod
    def load_state_from_file(cls, filename: str = STATE_FILENAME) -> Optional["ZinoState"]:
        """Loads and returns a previously persisted ZinoState from a JSON file dump.

        :returns: A ZinoState object if the state file was found, None if it wasn't.  If the state file is invalid or
                  otherwise unparseable, the underlying exceptions will be the callers responsibility to handle.
        """
        _log.info("Loading saved state from %s", filename)
        try:
            with open(filename, "r") as statefile:
                json_state = json.load(statefile)
            loaded_state = cls.model_validate(json_state)
        except FileNotFoundError:
            _log.error("No state file found (%s), starting from scratch ", filename)
            return
        else:
            return loaded_state
