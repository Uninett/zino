import datetime
from collections import namedtuple
from typing import Optional, Tuple

from zino.statemodels import Event, EventState, EventType, PortOrIPAddress

EventIndex = namedtuple("EventIndex", "router port event_type")


class Events:
    def __init__(self):
        self._events = {}
        self._events_by_index = {}
        self._last_event_id = 0

    def __getitem__(self, item):
        return self._events[item]

    def __len__(self):
        return len(self._events)

    def get_or_create_event(
        self, device_name: str, port: Optional[PortOrIPAddress], event_type: EventType
    ) -> Tuple[Event, bool]:
        """Creates a new event for the given event identifers, or, if one matching this identifier already exists,
        returns that.

        :returns: (Event, created) where Event is the existing or newly created Event object, while created is a boolean
                  indicating whether the returned object was just created by this method or if it existed from before.

        """
        try:
            return self.create_event(device_name, port, event_type), True
        except EventExistsError:
            return self.get(device_name, port, event_type), False

    def create_event(self, device_name: str, port: Optional[PortOrIPAddress], event_type: EventType) -> Event:
        index = EventIndex(device_name, port, event_type)
        if index in self._events_by_index:
            raise EventExistsError(f"Event for {index} already exists")

        event_id = self._last_event_id + 1
        self._last_event_id = event_id

        now = datetime.datetime.now()
        event = Event(
            id=event_id,
            router=device_name,
            port=port,
            event_type=event_type,
            state=EventState.EMBRYONIC,
            opened=now,
            updated=now,
        )
        self._events[event_id] = event
        self._events_by_index[index] = event
        return event

    def get(self, device_name: str, port: Optional[PortOrIPAddress], event_type: EventType) -> Event:
        index = EventIndex(device_name, port, event_type)
        return self._events.get(index)


class EventExistsError(Exception):
    pass
