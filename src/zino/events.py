import logging
from collections import namedtuple
from typing import Dict, Optional, Tuple, Type, Union

from pydantic.main import BaseModel

from zino.statemodels import (
    AlarmEvent,
    BFDEvent,
    BGPEvent,
    Event,
    EventState,
    PortOrIPAddress,
    PortStateEvent,
    ReachabilityEvent,
)
from zino.time import now

EventIndex = namedtuple("EventIndex", "router port type")

_log = logging.getLogger(__name__)


class Events(BaseModel):
    events: Dict[int, Union[PortStateEvent, BGPEvent, BFDEvent, ReachabilityEvent, AlarmEvent, Event]] = {}
    last_event_id: int = 0
    _events_by_index: Dict[EventIndex, Event] = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._rebuild_indexes()

    def __getitem__(self, item):
        return self.events[item]

    def __len__(self):
        return len(self.events)

    def _rebuild_indexes(self):
        """Rebuilds the event index from the current dict of events.

        Mostly useful when this object was constructed from dumped data, of which the index isn't a part.
        """
        new_index: Dict[EventIndex, Event] = {}
        for event in self.events.values():
            key = EventIndex(event.router, event.port, type(event))
            new_index[key] = event
        self._events_by_index = new_index

    def get_or_create_event(
        self,
        device_name: str,
        port: Optional[PortOrIPAddress],
        event_class: Type[Event],
    ) -> Tuple[Event, bool]:
        """Creates a new event for the given event identifiers, or, if one matching this identifier already exists,
        returns that.

        :returns: (Event, created) where Event is the existing or newly created Event object, while created is a boolean
                  indicating whether the returned object was just created by this method or if it existed from before.

        """
        try:
            return self.create_event(device_name, port, event_class), True
        except EventExistsError:
            return self.get(device_name, port, event_class), False

    def create_event(self, device_name: str, port: Optional[PortOrIPAddress], event_class: Type[Event]) -> Event:
        """Creates a new event for the given event identifiers. If an event already exists for this combination of
        identifiers, an EventExistsError is raised.

        """
        index = EventIndex(device_name, port, event_class)
        if index in self._events_by_index:
            raise EventExistsError(f"Event for {index} already exists")

        event_id = self.last_event_id + 1
        self.last_event_id = event_id

        event = event_class(
            id=event_id,
            router=device_name,
            port=port,
            state=EventState.EMBRYONIC,
            opened=now(),
        )
        _log.debug("created event %r", event)

        self.events[event_id] = event
        self._events_by_index[index] = event
        _log.debug("created %r", event)
        return event

    def get(self, device_name: str, port: Optional[PortOrIPAddress], event_class: Type[Event]) -> Event:
        """Returns an event based on its identifiers, None if no match was found"""
        index = EventIndex(device_name, port, event_class)
        return self._events_by_index.get(index)

    def checkout(self, event_id: int) -> Event:
        """Checks out a copy of an event that can be freely modified without being persisted"""
        return self[event_id].model_copy(deep=True)

    def commit(self, event: Event):
        """Commits an Event object to the state, replacing any existing event by the same id.

        If the event, for some reason, does not replace an existing event, indexes are rebuilt. This entrusts the
        committer to not change the identifying index attributes of a modified event.
        """
        if event.state == EventState.EMBRYONIC:
            event.state = EventState.OPEN
            event.opened = now()

        is_new = event.id not in self
        self.events[event.id] = event
        if is_new:
            self._rebuild_indexes()


class EventExistsError(Exception):
    pass
