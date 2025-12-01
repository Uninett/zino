import logging
from datetime import datetime, timezone

from zino.flaps import FlappingState
from zino.state import ZinoState
from zino.stateconverter.linedata import LineData
from zino.stateconverter.utils import OldState

_log = logging.getLogger(__name__)


def set_flapping_state(old_state: OldState, new_state: ZinoState):
    for linedata in old_state["::firstFlap"]:
        _set_first_flap(linedata, new_state)
    for linedata in old_state["::flapHistVal"]:
        _set_flap_hist_val(linedata, new_state)
    for linedata in old_state["::flappedAboveThreshold"]:
        _set_flapped_above_threshold(linedata, new_state)
    for linedata in old_state["::flapping"]:
        _set_flapping(linedata, new_state)
    for linedata in old_state["::flaps"]:
        _set_flaps(linedata, new_state)
    for linedata in old_state["::lastFlap"]:
        _set_last_flap(linedata, new_state)
    for linedata in old_state["::lastAge"]:
        _set_last_age(linedata, new_state)


def _set_first_flap(linedata: LineData, state: ZinoState):
    timestamp = datetime.fromtimestamp(int(linedata.value), tz=timezone.utc)
    _get_flapping_state_for(linedata, state).first_flap = timestamp


def _set_flap_hist_val(linedata: LineData, state: ZinoState):
    _get_flapping_state_for(linedata, state).hist_val = float(linedata.value)


def _set_flapped_above_threshold(linedata: LineData, state: ZinoState):
    _get_flapping_state_for(linedata, state).flapped_above_threshold = bool(int(linedata.value))


def _set_flapping(linedata: LineData, state: ZinoState):
    # This really isn't a persisted attribute in Zino 2, it is always calculated on the fly
    pass


def _set_flaps(linedata: LineData, state: ZinoState):
    _get_flapping_state_for(linedata, state).flaps = int(linedata.value)


def _set_last_flap(linedata: LineData, state: ZinoState):
    timestamp = datetime.fromtimestamp(int(linedata.value), tz=timezone.utc)
    _get_flapping_state_for(linedata, state).last_flap = timestamp


def _set_last_age(linedata: LineData, state: ZinoState):
    timestamp = datetime.fromtimestamp(int(linedata.value), tz=timezone.utc)
    _get_flapping_state_for(linedata, state).last_age = timestamp


def _get_flapping_state_for(linedata: LineData, state: ZinoState) -> FlappingState:
    device, port = linedata.identifiers
    index = (device, int(port))
    return state.flapping.interfaces.setdefault(index, FlappingState())
