import datetime
import logging
from typing import TYPE_CHECKING, Dict, Literal, Optional, Protocol

from pydantic.main import BaseModel

from zino.statemodels import (
    AlarmEvent,
    DeviceState,
    Event,
    EventState,
    PlannedMaintenance,
    Port,
    PortStateEvent,
    ReachabilityEvent,
)

if TYPE_CHECKING:
    from zino.state import ZinoState

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
            return [pm for pm in self.planned_maintenances if self.last_run < pm.start_time <= now < pm.end_time]
        else:
            return [pm for pm in self.planned_maintenances if pm.start_time <= now < pm.end_time]

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
        return [pm for pm in self.planned_maintenances.values() if pm.start_time < now < pm.end_time]

    def get_old_planned_maintenances(self, now: datetime.datetime) -> list[PlannedMaintenance]:
        """Returns all planned maintenances that should get deleted


        This means it has been 3 days since end_time
        """
        return [pm for pm in self.planned_maintenances.values() if now - pm.end_time > datetime.timedelta(days=3)]

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

        # Initiate PM once it becomes active
        for started_pm in self.get_started_planned_maintenances(now=now):
            self._start(state, started_pm)

        # Make sure all events that matches a PM is ignored
        for event in state.events:
            self._check_event(state, event)

        # End a PM and set events matching the PM to open
        for ended_pm in self.get_ended_planned_maintenances(now=now):
            self._end(state, ended_pm)

        old_pms = self.get_old_planned_maintenances(now)
        for pm in old_pms:
            self.close_planned_maintenance(pm.id, "timer expiry for old PMs", "zino")

        self.last_run = now

    def _start(self, state: "ZinoState", pm: PlannedMaintenance):
        events = self._get_or_create_events(state, pm)
        for event in events:
            # get special handling of embryonic -> open transition first
            state.events.commit(event)

            event.state = EventState.IGNORED
            state.events.commit(event)
            pm.event_ids.append(event.id)

    def _check_event(self, state: "ZinoState", event: Event):
        if event.state in [EventState.IGNORED, EventState.CLOSED]:
            return

        active_pms = self.get_active_planned_maintenances()
        for pm in active_pms:
            if pm.matches_event(event):
                event.state = EventState.IGNORED
                event.add_log(f"entered into existing active PM event id {pm.id}")
                state.events.commit(event)

    def _end(self, state: "ZinoState", pm: PlannedMaintenance):
        for event_id in pm.event_ids:
            event = state.events[event_id]
            event.state = EventState.OPEN
            state.events.commit(event)

    def _get_or_create_events(self, state: "ZinoState", pm: PlannedMaintenance) -> list[Event]:
        """Creates/gets events that are affected by the given starting planned
        maintenance
        """
        if pm.state == "portstate":
            return self._get_or_create_portstate_events(state, pm)
        elif pm.state == "device":
            return self._get_or_create_device_events(state, pm)
        raise ValueError(f"Invalid state {pm.state}")

    def _get_or_create_portstate_events(self, state: "ZinoState", pm: PlannedMaintenance) -> list[Event]:
        events = []
        deviceports = self._get_matching_ports(state, pm)
        for device, port in deviceports:
            event = state.events.get_or_create_event(device.name, port.ifindex, PortStateEvent)
            events.append(event)
        return events

    def _get_matching_ports(self, state: "ZinoState", pm) -> list[tuple[DeviceState, Port]]:
        ports = []
        for device in state.devices:
            for port in device.ports:
                if pm.matches_portstate(device, port):
                    ports.append((device, port))
        return ports

    def _get_or_create_device_events(self, state: "ZinoState", pm: PlannedMaintenance) -> list[Event]:
        events = []
        # all devices that the pm should affect
        devices = [device for device in state.devices if pm.matches_device(device)]
        for device in devices:
            reachability_event = state.events.get_or_create_event(device.name, None, ReachabilityEvent)
            yellow_event = state.events.get_or_create_event(device.name, "yellow", AlarmEvent)
            red_event = state.events.get_or_create_event(device.name, "red", AlarmEvent)
            for event in (reachability_event, yellow_event, red_event):
                events.append(event)
        return events
