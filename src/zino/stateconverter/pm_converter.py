import logging
from datetime import datetime

from zino.state import ZinoState
from zino.stateconverter.linedata import LineData
from zino.stateconverter.utils import OldState

_log = logging.getLogger(__name__)


def set_pm_state(old_state: OldState, new_state: ZinoState):
    _set_pm_attrs(old_state, new_state)
    for linedata in old_state["pm::pm_events"]:
        _set_pm_events(linedata, new_state)
    for linedata in old_state["::pm::lastid"]:
        _set_last_id(linedata, new_state)
    for linedata in old_state["::pm::lasttime"]:
        _set_last_time(linedata, new_state)


def _set_last_id(linedata: LineData, state: ZinoState):
    """Sets the last planned maintenance id"""
    state.planned_maintenances.last_pm_id = int(linedata.value)


def _set_last_time(linedata: LineData, state: ZinoState):
    """Sets timestamp for last time planned maintenance was run"""
    timestamp = int(linedata.value)
    state.planned_maintenances.last_run = datetime.fromtimestamp(timestamp)


def _set_pm_events(linedata: LineData, state: ZinoState):
    """Planned Maintenance events"""
    _log.info("pm_events is not supported")


def _set_pm_attrs(old_state: OldState, new_state: ZinoState):
    """Should set attributes for PlannedMaintenance objects"""
    _log.info("pm_attrs is not supported")
