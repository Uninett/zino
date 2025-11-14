"""This module exists to hold global state for a Zino process"""

__all__ = ["polldevs", "ZinoState"]

import json
import logging
import os
from collections import defaultdict
from typing import Dict, Optional

from pydantic import BaseModel, Field

from zino.config.models import Configuration, IPAddress, PollDevice
from zino.events import EventIndex, Events
from zino.flaps import FlappingStates
from zino.planned_maintenance import PlannedMaintenances
from zino.statemodels import DeviceStates, EventState
from zino.utils import log_time_spent

_log = logging.getLogger(__name__)

# Dictionary of configured devices
polldevs: Dict[str, PollDevice] = {}

# Global (sic) state
state: "ZinoState" = None

config: Configuration = Configuration()

# Last time the pollfile was modified
pollfile_mtime: Optional[float] = None


class ZinoState(BaseModel):
    """Holds all state that Zino needs to persist between runtimes"""

    devices: DeviceStates = Field(default_factory=DeviceStates)
    events: Events = Field(default_factory=Events)
    addresses: dict[IPAddress, str] = {}
    planned_maintenances: PlannedMaintenances = Field(default_factory=PlannedMaintenances)
    flapping: FlappingStates = Field(default_factory=FlappingStates)

    @log_time_spent()
    def dump_state_to_file(self, filename: str):
        """Dumps the full state to a file in JSON format"""
        _log.debug("dumping state to %s", filename)
        temp_file = f"{filename}.tmp"
        with open(temp_file, "w") as statefile:
            statefile.write(self.model_dump_json(exclude_none=True, indent=2))
        os.replace(src=temp_file, dst=filename)

    @classmethod
    @log_time_spent()
    def load_state_from_file(cls, filename: str) -> Optional["ZinoState"]:
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


def clean_state(state: ZinoState) -> None:
    """Cleans up a ZinoState object in-place.

    This involves detecting inconsistencies in the state data, typically stemming from bugs in older versions of
    Zino.
    """
    resolve_duplicate_events(state)


def resolve_duplicate_events(state: ZinoState) -> None:
    """Resolves duplicate events in the ZinoState object in-place.

    Detects and reports Event objects that share the same EventIndex (router, subindex, type).
    This helps identify duplicate events that shouldn't exist in the state.
    """
    duplicate_indices = _find_duplicate_events(state)
    if not duplicate_indices:
        return

    _log.warning(
        "Found %d duplicate events in saved state, removing duplicates by closing youngest events",
        len(duplicate_indices),
    )

    events_closed_count = 0

    for event_index, events_list in duplicate_indices.items():
        _log.debug("EventIndex %s matches %d events:", event_index, len(events_list))

        # Sort events by opened timestamp to find the oldest (original)
        events_sorted = sorted(events_list, key=lambda x: x[1].opened)

        # Keep the oldest event, close all others
        oldest_id, oldest_event = events_sorted[0]

        _log.debug("  Keeping oldest event: Event ID %s (opened=%s)", oldest_id, oldest_event.opened)

        # Close all duplicate events except the oldest
        for event_id, event in events_sorted[1:]:
            _log.debug("  Closing duplicate: Event ID %s (opened=%s)", event_id, event.opened)
            old_state = event.state
            event.state = EventState.CLOSED
            # Add log entry to the event
            event.add_log(f"Event closed automatically during cleanup: duplicate of event {oldest_id}")
            event.add_history(f"state change {old_state.value} -> closed (duplicate)")
            events_closed_count += 1

    # Rebuild the event index and log summary if any events were closed
    if events_closed_count > 0:
        _log.info("Forcibly closed %d duplicate events", events_closed_count)
        _log.debug("Rebuilding event indexes after closing duplicates")
        state.events._rebuild_indexes()


def _find_duplicate_events(state: ZinoState) -> dict[EventIndex, list]:
    """Finds all Event objects that share the same EventIndex.

    Returns a dictionary mapping EventIndex to lists of (event_id, event) tuples
    where there are duplicates (more than one event with the same index).
    """
    # Build a mapping of EventIndex -> list of events with that index
    duplicates_map = defaultdict(list)

    for event_id, event in state.events.events.items():
        if event.state == EventState.CLOSED:
            continue

        # Create the EventIndex for this event
        event_index = EventIndex(router=event.router, subindex=event.subindex, type=type(event))
        duplicates_map[event_index].append((event_id, event))

    # Find all EventIndex values with more than one event
    duplicate_indices = {event_index: events for event_index, events in duplicates_map.items() if len(events) > 1}

    return duplicate_indices
