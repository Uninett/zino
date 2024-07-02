import logging

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
    for linedata in old_state["::lastFlap"]:
        _set_last_age(linedata, new_state)


def _set_first_flap(linedata: LineData, state: ZinoState):
    _log.info("firstFlap is not supported")


def _set_flap_hist_val(linedata: LineData, state: ZinoState):
    _log.info("flapHistVal is not supported")


def _set_flapped_above_threshold(linedata: LineData, state: ZinoState):
    _log.info("flappedAboveThreshold is not supported")


def _set_flapping(linedata: LineData, state: ZinoState):
    _log.info("flapping is not supported")


def _set_flaps(linedata: LineData, state: ZinoState):
    _log.info("flaps is not supported")


def _set_last_flap(linedata: LineData, state: ZinoState):
    _log.info("lastFlap is not supported")


def _set_last_age(linedata: LineData, state: ZinoState):
    """This is related to flapping"""
    _log.info("lastAge is is not supported")
