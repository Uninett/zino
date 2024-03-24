import datetime
import logging
from typing import Dict, Literal, Optional, Protocol

from pydantic.main import BaseModel

from zino.statemodels import Event, EventState, PlannedMaintenance

_log = logging.getLogger(__name__)


class PlannedMaintenanceObserver(Protocol):
    """Defines a valid protocol for planned maintenance observer functions"""

    def __call__(self) -> None:
        ...


class PlannedMaintenances(BaseModel):
    planned_maintenances: Dict[int, PlannedMaintenance] = {}
    last_pm_id: int = 0
    last_run: Optional[datetime.datetime] = None
    _observers: list[PlannedMaintenanceObserver] = []

    def __getitem__(self, item):
        return self.planned_maintenances[item]

    def __len__(self):
        return len(self.planned_maintenances)

    def create_planned_maintenance(
        self,
        start_time: datetime.datetime,
        end_time: datetime.datetime,
        type: Literal["portstate", "device"],
        match_type: Literal["regexp", "str", "exact", "intf-regexp"],
        match_expression: str,
        match_device: Optional[str],
    ) -> int:
        """Creates a planned maintenance, adds it to the planned_maintenances dict and
        returns its id
        """
        pm_id = self.get_next_available_pm_id()
        pm = PlannedMaintenance(
            id=pm_id,
            start_time=start_time,
            end_time=end_time,
            type=type,
            match_type=match_type,
            match_expression=match_expression,
            match_device=match_device,
        )
        self.planned_maintenances[pm_id] = pm
        self._call_observers()

    def close_planned_maintenance(self, id: int, reason: str, user: str) -> None:
        """Deletes planned maintenance with the given id"""
        # See `close` function in Zino 1.0 `pm.tcl`
        pm = self.planned_maintenances.get(id, None)
        if not pm:
            # TODO figure out if this is enough
            return
        pm.add_log("PM closed by %s: %s", user, reason)
        del self.planned_maintenances[id]
        self._call_observers()

    def get_started_planned_maintenances(self, now: datetime.datetime) -> list[PlannedMaintenance]:
        """Returns all planned maintenances that have began since the last run of this
        task until now
        """
        if self.last_run:
            return [pm for pm in self.planned_maintenances if self.last_run < pm.start_time <= now]
        else:
            return [pm for pm in self.planned_maintenances if pm.start_time <= now]

    def get_ended_planned_maintenances(self, now: datetime.datetime) -> list[PlannedMaintenance]:
        """Returns all planned maintenances that have ended since the last run of this
        task until now
        """
        if self.last_run:
            return [pm for pm in self.planned_maintenances if self.last_run < pm.end_time <= now]
        else:
            return [pm for pm in self.planned_maintenances if pm.end_time <= now]

    def get_active_planned_maintenances(self) -> list[PlannedMaintenance]:
        """Returns all planned maintenances that are currently active

        This means it has started latest now and the end_time is later than now
        """
        now = datetime.datetime.now()
        return [pm for pm in self.planned_maintenances if pm.start_time < now < pm.end_time]

    def add_pm_observer(self, observer: PlannedMaintenanceObserver) -> None:
        """Adds an observer function that will be called any time a planned maintenance
        is added or removed
        """
        self._observers.append(observer)

    def get_next_available_pm_id(self) -> int:
        """Returns the next available planned maintenance id"""
        self.last_pm_id += 1
        return self.last_pm_id

    def _call_observers(self) -> None:
        for observer in self._observers:
            observer()

    def periodic(self):
        from zino.state import state

        now = datetime.datetime.now()

        started_maintenances = self.get_started_planned_maintenances(now=now)
        for started_pm in started_maintenances:
            events = self._get_or_create_maintenance_events_for_maintenance_start(maintenance=started_pm)
            for event in events:
                self._ignore_event(event)
                started_pm.event_ids.append(event.id)

        active_maintenances = self.get_active_planned_maintenances(now=now)
        # Get all events (maybe already filter here for ignored and closed events?)
        for event in state.events:
            for active_pm in active_maintenances:
                if active_pm.matches(event):
                    self._ignore_event(event)
                    active_pm.event_ids.append(event.id)

        ended_maintenances = self.get_ended_planned_maintenances(now=now)
        for ended_pm in ended_maintenances:
            for event in ended_pm.pm_events:
                if event.state is not EventState.OPEN:
                    self._unignore_event(event)

    def _ignore_event(self, event: Event):
        from zino.state import state

        event.state = EventState.IGNORED
        state.events.commit(event)

    def _unignore_event(self, event: Event):
        from zino.state import state

        # This is how it is currently done in Zino 1.0
        # Could use some improvement on detecting the actual correct state
        event.state = EventState.OPEN
        state.events.commit(event)

    def _get_or_create_maintenance_events_for_maintenance_start(self, maintenance: PlannedMaintenance) -> list[Event]:
        """Creates/gets events that are affected by the given starting planned
        maintenance
        """
        # See `start_pm` function in Zino 1.0 `pm.tcl`
        pass
