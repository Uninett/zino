from zino.state import ZinoState
from zino.stateconverter.linedata import LineData
from zino.stateconverter.utils import OldState, parse_ip
from zino.statemodels import BFDSessState, BFDState, Port


def set_bfd_state(
    old_state: OldState,
    new_state: ZinoState,
):
    for linedata in old_state["::bfdSessState"]:
        _set_bfd_sess_state(linedata, new_state)
    for linedata in old_state["::bfdSessAddr"]:
        _set_bfd_sess_addr(linedata, new_state)
    for linedata in old_state["::bfdSessDiscr"]:
        _set_bfd_sess_discr(linedata, new_state)


def _set_bfd_sess_addr(linedata: LineData, state: ZinoState):
    """Requires the matching Port and BFDState object to exist"""
    if not linedata.value:
        return
    device = state.devices.get(linedata.identifiers[0])
    ifindex = int(linedata.identifiers[1])
    port = device.ports[ifindex]
    port.bfd_state.session_addr = parse_ip(linedata.value)


def _set_bfd_sess_state(linedata: LineData, state: ZinoState):
    device = state.devices.get(linedata.identifiers[0])
    ifindex = int(linedata.identifiers[1])
    sess_state = BFDSessState(linedata.value)
    if ifindex not in device.ports:
        device.ports[ifindex] = Port(ifindex=ifindex)
    port = device.ports[ifindex]
    if not port.bfd_state:
        port.bfd_state = BFDState(session_state=sess_state)
    port.bfd_state.session_state = sess_state


def _set_bfd_sess_discr(linedata: LineData, state: ZinoState):
    """Requires the matching Port and BFDState object to exist"""
    device = state.devices.get(linedata.identifiers[0])
    ifindex = int(linedata.identifiers[1])
    port = device.ports[ifindex]
    port.bfd_state.session_discr = int(linedata.value)
