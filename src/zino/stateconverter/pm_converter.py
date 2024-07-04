import logging
from datetime import datetime

from zino.state import ZinoState
from zino.stateconverter.linedata import LineData
from zino.stateconverter.utils import OldState, parse_log_and_history
from zino.statemodels import (
    DeviceMaintenance,
    MatchType,
    PlannedMaintenance,
    PmType,
    PortStateMaintenance,
)

_log = logging.getLogger(__name__)


PM_CLASS_MAPPING = {
    PmType.PORTSTATE: PortStateMaintenance,
    PmType.DEVICE: DeviceMaintenance,
}


def set_pm_state(old_state: OldState, new_state: ZinoState):
    _set_pm_event_attrs(old_state, new_state)
    for linedata in old_state["::pm::pm_events"]:
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
    """Registers events affected by planned maintenance"""
    pm_id = int(linedata.identifiers[0])
    try:
        pm = state.planned_maintenances[pm_id]
    except KeyError:
        _log.error(f"Could not find planned maintenance with id {pm_id}")
        return
    pm.event_ids = [int(id) for id in linedata.value.split()]


def _set_pm_event_attrs(old_state: OldState, new_state: ZinoState):
    """Created PlannedMaintenance objects from pm_event attributes"""
    pm_data = _group_pm_attrs_by_id(old_state)
    for id, attrs in pm_data.items():
        try:
            pm = _create_pm(attrs)
            pm.id = id
            new_state.planned_maintenances.planned_maintenances[id] = pm
        except ValueError as e:
            _log.error(f"Error setting pm_event attribute: {str(e)}")


def _create_pm(attrs: dict[str, str]) -> PlannedMaintenance:
    """Creates a PlannedMaintenance object from attributes"""

    required_attrs = ["starttime", "endtime", "match_type", "match_expr", "type"]
    for required_attr in required_attrs:
        if required_attr not in attrs:
            raise ValueError(f"Required attribute '{required_attr}' not found in pm_event")

    start_time = datetime.fromtimestamp(int(attrs["starttime"]))
    end_time = datetime.fromtimestamp(int(attrs["endtime"]))
    match_type = MatchType(attrs["match_type"])
    match_expression = attrs["match_expr"]
    match_device = attrs.get("match_dev")
    pm_type = PmType(attrs["type"])
    log = parse_log_and_history(attrs.get("log", ""))

    pm_class = PM_CLASS_MAPPING.get(pm_type)
    if pm_class is None:
        raise ValueError(f"Unknown pm_event type {pm_type}")

    pm = pm_class(
        start_time=start_time,
        end_time=end_time,
        match_type=match_type,
        match_expression=match_expression,
        match_device=match_device,
        log=log,
    )

    return pm


def _group_pm_attrs_by_id(old_state: OldState) -> dict[int, dict[str, str]]:
    """Returns a dict of dicts with mapping from pm_event ID to pm_event attributes"""
    return_dict = dict()
    for linedata in old_state["::pm::event"]:
        pm_attr = linedata.identifiers[0]
        pm_id = int(linedata.identifiers[1])
        if pm_id not in return_dict:
            return_dict[pm_id] = dict()
        return_dict[pm_id][pm_attr] = linedata.value
    return return_dict
