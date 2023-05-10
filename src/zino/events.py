import logging
from collections import namedtuple
from typing import Optional, Tuple

from pydantic.main import BaseModel

from zino.statemodels import Event, EventState, EventType, PortOrIPAddress
from zino.time import now

EventIndex = namedtuple("EventIndex", "router port event_type")

_log = logging.getLogger(__name__)


class Events(BaseModel):
    events: dict = {}
    last_event_id: int = 0
    _events_by_index: dict = {}

    class Config:
        underscore_attrs_are_private = True

    def __getitem__(self, item):
        return self.events[item]

    def __len__(self):
        return len(self.events)

    def get_or_create_event(
        self, device_name: str, port: Optional[PortOrIPAddress], event_type: EventType
    ) -> Tuple[Event, bool]:
        """Creates a new event for the given event identifiers, or, if one matching this identifier already exists,
        returns that.

        :returns: (Event, created) where Event is the existing or newly created Event object, while created is a boolean
                  indicating whether the returned object was just created by this method or if it existed from before.

        """
        try:
            return self.create_event(device_name, port, event_type), True
        except EventExistsError:
            return self.get(device_name, port, event_type), False

    def create_event(self, device_name: str, port: Optional[PortOrIPAddress], event_type: EventType) -> Event:
        """Creates a new event for the given event identifiers. If an event already exists for this combination of
        identifiers, an EventExistsError is raised.

        """
        index = EventIndex(device_name, port, event_type)
        if index in self._events_by_index:
            raise EventExistsError(f"Event for {index} already exists")

        event_id = self.last_event_id + 1
        self.last_event_id = event_id

        event = Event(
            id=event_id,
            router=device_name,
            port=port,
            event_type=event_type,
            state=EventState.EMBRYONIC,
            opened=now(),
        )
        self.events[event_id] = event
        self._events_by_index[index] = event
        _log.debug("created %r", event)
        return event

    def get(self, device_name: str, port: Optional[PortOrIPAddress], event_type: EventType) -> Event:
        """Returns an event based on its identifiers, None if no match was found"""
        index = EventIndex(device_name, port, event_type)
        return self._events_by_index.get(index)


class EventExistsError(Exception):
    pass
