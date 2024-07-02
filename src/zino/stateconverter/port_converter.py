import logging

from zino.state import ZinoState
from zino.stateconverter.linedata import LineData
from zino.stateconverter.utils import OldState
from zino.statemodels import InterfaceState, Port

_log = logging.getLogger(__name__)


def set_port_state(old_state: OldState, new_state: ZinoState):
    for linedata in old_state["::portState"]:
        _set_interface_state(linedata, new_state)
    for linedata in old_state["::portToIfDescr"]:
        _set_port_to_if_descr(linedata, new_state)
    for linedata in old_state["::portToLocIfDescr"]:
        _set_port_to_loc_if_descr(linedata, new_state)


def _set_interface_state(linedata: LineData, state: ZinoState):
    device = state.devices.get(linedata.identifiers[0])
    ifindex = int(linedata.identifiers[1])
    if ifindex not in device.ports:
        device.ports[ifindex] = Port(ifindex=ifindex)
    if linedata.value == "flapping":
        _log.info("flapping port state is not supported")
        return
    device.ports[ifindex].state = InterfaceState(linedata.value)


def _set_port_to_if_descr(linedata: LineData, state: ZinoState):
    device = state.devices.get(linedata.identifiers[0])
    ifindex = int(linedata.identifiers[1])
    if ifindex not in device.ports:
        device.ports[ifindex] = Port(ifindex=ifindex)
    device.ports[ifindex].ifdescr = linedata.value


def _set_port_to_loc_if_descr(linedata: LineData, state: ZinoState):
    """Sets ifalias value"""
    device = state.devices.get(linedata.identifiers[0])
    ifindex = int(linedata.identifiers[1])
    if ifindex not in device.ports:
        device.ports[ifindex] = Port(ifindex=ifindex)
    device.ports[ifindex].ifalias = linedata.value
