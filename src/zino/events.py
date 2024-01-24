import logging
from typing import Dict, NamedTuple, Optional, Protocol, Type, Union

from pydantic.main import BaseModel

from zino.statemodels import (
    AlarmEvent,
    BFDEvent,
    BGPEvent,
    Event,
    EventState,
    PortStateEvent,
    ReachabilityEvent,
    SubIndex,
)

_log = logging.getLogger(__name__)


class EventIndex(NamedTuple):
    router: str
    port: SubIndex
    type: Type


class EventObserver(Protocol):
    """Defines a valid protocol for event observer functions"""

    def __call__(self, new_event: Event, old_event: Optional[Event] = None) -> None:
        ...


class Events(BaseModel):
    events: Dict[int, Union[PortStateEvent, BGPEvent, BFDEvent, ReachabilityEvent, AlarmEvent, Event]] = {}
    last_event_id: int = 0
    _events_by_index: Dict[EventIndex, Event] = {}
    _observers: list[EventObserver] = []

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
            key = EventIndex(event.router, event.subindex, type(event))
            new_index[key] = event
        self._events_by_index = new_index

    def get_or_create_event(
        self,
        device_name: str,
        port: SubIndex,
        event_class: Type[Event],
    ) -> Event:
        """Creates and returns a new event for the given event identifiers, or, if an event matching this identifier
        already exists in the index, returns that.

        A new event is not immediately committed to the event index; this must be done by explicitly calling the
        `commit()` method.  I.e. the caller can assume that when the returned `Event` object's `id` value is `None`,
        it is a new event.

        If a matching event already exists, the return value is a checkout copy, as if the `checkout()` method had been
        used.  The assumption is that the caller is looking to make changes to the fetched event.
        """
        try:
            return self.create_event(device_name, port, event_class)
        except EventExistsError:
            event = self.get(device_name, port, event_class)
            return self.checkout(event.id)

    def create_event(self, device_name: str, port: SubIndex, event_class: Type[Event]) -> Event:
        """Creates a new event for the given event identifiers. If an event already exists for this combination of
        identifiers, an EventExistsError is raised.

        The event is not committed to the event registry; this must be done by explicitly calling the `commit()` method.
        """
        index = EventIndex(device_name, port, event_class)
        if index in self._events_by_index:
            raise EventExistsError(f"Event for {index} already exists")

        event = event_class(
            router=device_name,
        )
        _log.debug("created embryonic event %r", event)
        return event

    def get(self, device_name: str, port: SubIndex, event_class: Type[Event]) -> Event:
        """Returns an event based on its identifiers, None if no match was found"""
        index = EventIndex(device_name, port, event_class)
        return self._events_by_index.get(index)

    def checkout(self, event_id: int) -> Event:
        """Checks out a copy of an event that can be freely modified without being persisted"""
        return self[event_id].model_copy(deep=True)

    def commit(self, event: Event, user: str = "monitor"):
        """Commits an Event object to the state, replacing any existing event by the same id.

        If the event does not have an id, it is considered a new event and is assigned a new id value before it is
        placed in the event index.

        This all assumes the committer does not change the identifying index attributes of an existing event that it
        has modified, as that will break the index.
        """
        if event.state == EventState.EMBRYONIC:
            event.set_state(EventState.OPEN, user)

        is_new = not event.id
        if is_new:
            old_event = None
            event.id = self.get_next_available_event_id()
        else:
            old_event = self.events[event.id]
        index = EventIndex(event.router, event.subindex, type(event))
        self._events_by_index[index] = event
        self.events[event.id] = event

        self._call_observers_for(new_event=event, old_event=old_event)

    def add_event_observer(self, observer: EventObserver):
        """Adds an observer function that will be called any time an event is committed"""
        self._observers.append(observer)

    def get_next_available_event_id(self):
        """Returns the next available event id"""
        self.last_event_id += 1
        return self.last_event_id

    def _call_observers_for(self, new_event: Event, old_event: Optional[Event] = None):
        for observer in self._observers:
            observer(new_event=new_event, old_event=old_event)


class EventExistsError(Exception):
    pass
