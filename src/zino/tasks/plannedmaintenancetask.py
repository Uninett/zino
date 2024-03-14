import datetime

from zino.planned_maintenance import matches_planned_maintenance
from zino.statemodels import Event, EventState, PlannedMaintenance
from zino.tasks.task import Task


class PlannedMaintenanceTask(Task):
    """Handles events when planned maintenance is happening"""

    async def run(self):
        now = datetime.datetime.now()
        started_maintenances = self.state.planned_maintenances.get_started_planned_maintenances(now=now)
        for maintenance in started_maintenances:
            events = self._get_or_create_maintenance_events_for_maintenance_start(maintenance=maintenance)
            for event in events:
                event.state = EventState.IGNORED
                self.state.events.commit(event)
                maintenance.pm_events.append(event)

        # Get all events (maybe already filter here for ignored and closed events?)
        events = []
        for event in events:
            for active_pm in self.state.planned_maintenances.get_active_planned_maintenances(now=now):
                if matches_planned_maintenance(event=event, maintenance=active_pm):
                    event.state = EventState.IGNORED
                    self.state.events.commit(event)
                    active_pm.pm_events.append(event)

        ended_maintenances = self.state.planned_maintenances.get_ended_planned_maintenances(now=now)
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
