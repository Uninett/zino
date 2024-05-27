import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Dict, Literal, Optional, Protocol

from pydantic.main import BaseModel

from zino.statemodels import Event, EventState, PlannedMaintenance

if TYPE_CHECKING:
    from zino.state import ZinoState

_log = logging.getLogger(__name__)


PM_EXPIRY_TIME = timedelta(days=3)


class PlannedMaintenanceObserver(Protocol):
    """Defines a valid protocol for planned maintenance observer functions"""

    def __call__(self) -> None:
        ...


class PlannedMaintenances(BaseModel):
    planned_maintenances: Dict[int, PlannedMaintenance] = {}
    last_pm_id: int = 0
    last_run: Optional[datetime] = datetime.fromtimestamp(0)
    _observers: list[PlannedMaintenanceObserver] = []

    def __getitem__(self, item):
        return self.planned_maintenances[item]

    def __len__(self):
        return len(self.planned_maintenances)

    def create_planned_maintenance(
        self,
        start_time: datetime,
        end_time: datetime,
        type: Literal["portstate", "device"],
        match_type: Literal["regexp", "str", "exact", "intf-regexp"],
        match_expression: str,
        match_device: Optional[str],
    ) -> PlannedMaintenance:
        """Creates a planned maintenance, adds it to the planned_maintenances dict and
        returns it
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
        return pm

    def close_planned_maintenance(self, id: int, reason: str, user: str) -> None:
        """Deletes planned maintenance with the given id"""
        # See `close` function in Zino 1.0 `pm.tcl`
        pm = self.planned_maintenances.get(id, None)
        if not pm:
            # TODO figure out if this is enough
            return
        pm.add_log(f"PM closed by {user}: {reason}")
        del self.planned_maintenances[id]
        self._call_observers()

    def get_started_planned_maintenances(self, now: datetime) -> list[PlannedMaintenance]:
        """Returns all planned maintenances that have begun since the last run of this
        task until `now`
        """
        return [pm for pm in self.planned_maintenances.values() if self.last_run < pm.start_time <= now < pm.end_time]

    def get_ended_planned_maintenances(self, now: datetime) -> list[PlannedMaintenance]:
        """Returns all planned maintenances that have ended since the last run of this
        task until `now`
        """
        return [pm for pm in self.planned_maintenances.values() if self.last_run < pm.end_time <= now]

    def get_active_planned_maintenances(self, now: datetime) -> list[PlannedMaintenance]:
        """Returns all planned maintenances that are currently active

        This means it has started before `now` and the end_time is later than `now`
        """
        return [pm for pm in self.planned_maintenances.values() if pm.start_time < now < pm.end_time]

    def get_old_planned_maintenances(self, now: datetime) -> list[PlannedMaintenance]:
        """Returns all planned maintenances that should get deleted

        This means that `now` is 3 days later than end_time
        """
        return [pm for pm in self.planned_maintenances.values() if now - pm.end_time > PM_EXPIRY_TIME]

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

    def periodic(self, state: "ZinoState"):
        now = datetime.now()

        # Initiate PM once it becomes active
        for started_pm in self.get_started_planned_maintenances(now=now):
            started_pm.start(state)

        # Make sure all events that match a PM is ignored
        for event in state.events.events.values():
            self._check_event(state, event, now)

        # Set events matching ended PMs to open
        for ended_pm in self.get_ended_planned_maintenances(now=now):
            ended_pm.end(state)

        # Delete events that have been closed for a certain amount of time
        old_pms = self.get_old_planned_maintenances(now)
        for pm in old_pms:
            self.close_planned_maintenance(pm.id, "timer expiry for old PMs", "zino")

        self.last_run = now

    def _check_event(self, state: "ZinoState", event: Event, now: datetime):
        if event.state in [EventState.IGNORED, EventState.CLOSED]:
            return

        active_pms = self.get_active_planned_maintenances(now)
        for pm in active_pms:
            if pm.matches_event(event, state):
                event.state = EventState.IGNORED
                event.add_log(f"entered into existing active PM event id {pm.id}")
                state.events.commit(event)
                pm.event_ids.append(event.id)
