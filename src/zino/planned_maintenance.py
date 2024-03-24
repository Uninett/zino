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
        # Note: last run (self.last_run) can be None, which would mean this task has never run before
        pass

    def get_ended_planned_maintenances(self, now: datetime.datetime) -> list[PlannedMaintenance]:
        """Returns all planned maintenances that have ended since the last run of this
        task until now
        """
        # Note: last run (self.last_run) can be None, which would mean this task has never run before
        pass

    def get_active_planned_maintenances(self, now: datetime.datetime) -> list[PlannedMaintenance]:
        """Returns all planned maintenances that are currently active

        This means it has started latest now and the end_time is later than now
        """

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
        now = datetime.datetime.now()

        started_maintenances = self.get_started_planned_maintenances(now=now)
        for maintenance in started_maintenances:
            events = self._get_or_create_maintenance_events_for_maintenance_start(maintenance=maintenance)
            for event in events:
                event.state = EventState.IGNORED
                self.state.events.commit(event)
                maintenance.pm_events.append(event)

        # Get all events (maybe already filter here for ignored and closed events?)
        events = []
        for event in events:
            for active_pm in self.get_active_planned_maintenances(now=now):
                if matches_planned_maintenance(event=event, maintenance=active_pm):
                    event.state = EventState.IGNORED
                    self.state.events.commit(event)
                    active_pm.pm_events.append(event)

        ended_maintenances = self.get_ended_planned_maintenances(now=now)
        for maintenance in ended_maintenances:
            for event in maintenance.pm_events:
                if event.state is not EventState.OPEN:
                    # This is how it is currently done in Zino 1.0
                    # Could use some improvement on detecting the actual correct state
                    event.state = EventState.OPEN
                    self.state.events.commit(event)

    def _get_or_create_maintenance_events_for_maintenance_start(self, maintenance: PlannedMaintenance) -> list[Event]:
        """Creates/gets events that are affected by the given starting planned
        maintenance
        """
        # See `start_pm` function in Zino 1.0 `pm.tcl`
        pass


def matches_planned_maintenance(event: Event, maintenance: PlannedMaintenance) -> bool:
    """Returns true if the given event matches the given maintenance"""
    pass
