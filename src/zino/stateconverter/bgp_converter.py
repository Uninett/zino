import logging
from typing import NamedTuple

from zino.state import ZinoState
from zino.stateconverter.utils import OldState, parse_ip
from zino.statemodels import BGPAdminStatus, BGPOperState, BGPPeerSession, IPAddress

_log = logging.getLogger(__name__)


def set_bgp_state(
    old_state: OldState,
    new_state: ZinoState,
):
    """Updates `bgp_peers` field for devices in `state` with
    BGP session data defined in `temp_sessions`. If errors occur for one peer,
    the error is logged and the peer is discarded before the next peer is processed.
    """
    sessions = _get_bgp_sessions(old_state)
    for index, session in sessions.items():
        device_name, peer_ip = index
        device = new_state.devices.get(device_name)
        device.bgp_peers[peer_ip] = session


class BGPDevicePeerIndex(NamedTuple):
    """Defines a device and a peer using the name of the device and the IP for the peer"""

    device: str
    ip: IPAddress


def _get_bgp_sessions(old_state: OldState) -> dict[BGPDevicePeerIndex, BGPPeerSession]:
    """Parses old state for BGP sessions and maps them to the correct device and peer IP"""
    bgp_data = _group_bgp_data_by_index(old_state)
    bgp_sessions = dict()
    for index, data in bgp_data.items():
        try:
            uptime = int(data["::bgpPeerUpTime"])
            admin_status = BGPAdminStatus(data["::bgpPeerAdminState"])
            oper_state = BGPOperState(data["::bgpPeerOperState"])
        except KeyError as e:
            _log.error(f"Missing BGP data for index {index}: {str(e)}")
            continue
        session = BGPPeerSession(uptime=uptime, admin_status=admin_status, oper_state=oper_state)
        bgp_sessions[index] = session
    return bgp_sessions


def _group_bgp_data_by_index(old_state: OldState) -> dict[BGPDevicePeerIndex, dict[str, str]]:
    """Goes through the state dict and groups BGP data by device and peer IP"""
    return_dict = dict()
    for key in ("::bgpPeerAdminState", "::bgpPeerOperState", "::bgpPeerUpTime"):
        for linedata in old_state[key]:
            try:
                ip = parse_ip(linedata.identifiers[1])
            except ValueError:
                # There is a bug in zino1 statedump where invalid IPv6 addresses are dumped
                _log.error(f"Could not parse ip {linedata.identifiers[1]}")
            device_name = linedata.identifiers[0]
            index = BGPDevicePeerIndex(device_name, ip)
            if index not in return_dict:
                return_dict[index] = dict()
            return_dict[index][key] = linedata.value
    return return_dict
