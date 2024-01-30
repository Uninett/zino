import logging
from dataclasses import dataclass, replace
from ipaddress import ip_address
from typing import Any, Iterable, Optional

from pyasn1.type.univ import OctetString

from zino.snmp import SparseWalkResponse
from zino.statemodels import (
    BGPAdminStatus,
    BGPEvent,
    BGPOperState,
    BGPPeerSession,
    BGPStyle,
    IPAddress,
)
from zino.tasks.task import Task

_logger = logging.getLogger(__name__)

TIME_BEFORE_OPER_DOWN_ALERT = 600

JUNIPER_TRANSLATION_MAP = [
    ("peer_state", "jnxBgpM2PeerState"),
    ("peer_admin_status", "jnxBgpM2PeerStatus"),
    ("peer_remote_address", "jnxBgpM2PeerRemoteAddr"),
    ("peer_remote_as", "jnxBgpM2PeerRemoteAs"),
    ("peer_fsm_established_time", "jnxBgpM2PeerFsmEstablishedTime"),
]
CISCO_TRANSLATION_MAP = [
    ("peer_state", "cbgpPeer2State"),
    ("peer_admin_status", "cbgpPeer2AdminStatus"),
    ("peer_remote_address", "cbgpPeer2RemoteAddr"),
    ("peer_remote_as", "cbgpPeer2RemoteAs"),
    ("peer_fsm_established_time", "cbgpPeer2FsmEstablishedTime"),
]
GENERAL_TRANSLATION_MAP = [
    ("peer_state", "bgpPeerState"),
    ("peer_admin_status", "bgpPeerAdminStatus"),
    ("peer_remote_address", "bgpPeerRemoteAddr"),
    ("peer_remote_as", "bgpPeerRemoteAs"),
    ("peer_fsm_established_time", "bgpPeerFsmEstablishedTime"),
]
LOCAL_AS_OBJECTS = {
    "juniper": ("BGP4-V2-MIB-JUNIPER", "jnxBgpM2PeerLocalAs"),
    "cisco": ("CISCO-BGP4-MIB", "cbgpLocalAs"),
    "general": ("BGP4-MIB", "bgpLocalAs"),
}
BUGGY_REMOTE_ADDRESSES = [
    # Bug in JunOS -- info from IPv6 BGP sessions spill over
    "0.0.0.0",
    # Bug in earlier Cisco IOS, info from elsewhere (IPv6?) spills over
    "32.1.7.0",
]


@dataclass
class BaseBGPRow:
    peer_state: BGPOperState
    peer_admin_status: BGPAdminStatus
    peer_remote_address: IPAddress
    peer_remote_as: int
    peer_fsm_established_time: int


class BGPStateMonitorTask(Task):
    """Fetches and stores state information about external BGP sessions."""

    async def run(self):
        bgp_style = await self._get_bgp_style()
        if bgp_style != self.device_state.bgp_style:
            _logger.debug(
                f"Router {self.device_state.name} changed its BGP style from '{self.device_state.bgp_style}' to "
                f"'{bgp_style}'"
            )
            self.device_state.bgp_style = bgp_style
        if not bgp_style:
            return

        local_as = await self._get_local_as(bgp_style=bgp_style)
        uptime = await self._get_uptime()
        if not local_as or not uptime:
            return

        if bgp_style == BGPStyle.JUNIPER:
            bgp_info = await self._get_juniper_bgp_info()
        elif bgp_style == BGPStyle.CISCO:
            bgp_info = await self._get_cisco_bgp_info()
        elif bgp_style == BGPStyle.GENERAL:
            bgp_info = await self._get_general_bgp_info()

        if not bgp_info:
            return

        bgp_info = self._fixup_ip_addresses(bgp_info=bgp_info)

        for result in bgp_info.values():
            self._update_single_bgp_entry(row=result, local_as=local_as, uptime=uptime)

    async def _get_bgp_style(self) -> Optional[BGPStyle]:
        if await self.snmp.subtree_is_supported("BGP4-V2-MIB-JUNIPER", "jnxBgpM2"):
            return BGPStyle.JUNIPER

        if await self.snmp.subtree_is_supported("CISCO-BGP4-MIB", "cbgpPeer2Table"):
            return BGPStyle.CISCO

        if await self.snmp.subtree_is_supported("BGP4-MIB", "bgp"):
            return BGPStyle.GENERAL

        return None

    async def _get_local_as(self, bgp_style: BGPStyle) -> Optional[int]:
        try:
            mib, object_name = LOCAL_AS_OBJECTS[bgp_style]
        except KeyError:
            return
        response = await self.snmp.getnext(mib, object_name)
        if self.snmp.is_in_scope(response, (mib, object_name)):
            return response.value
        else:
            _logger.info(f"router {self.device.name} misses {object_name}")

    async def _get_juniper_bgp_info(self) -> Optional[SparseWalkResponse]:
        variables = (
            "jnxBgpM2PeerState",
            "jnxBgpM2PeerStatus",
            "jnxBgpM2PeerRemoteAddr",
            "jnxBgpM2PeerRemoteAs",
            "jnxBgpM2PeerFsmEstablishedTime",
        )

        juniper_bgp_info = await self._get_bgp_info(mib_name="BGP4-V2-MIB-JUNIPER", variables=variables)

        if not juniper_bgp_info:
            return None

        juniper_bgp_info = self._transform_variables_from_specific_to_general(
            bgp_info=juniper_bgp_info, bgp_style=BGPStyle.JUNIPER
        )

        return juniper_bgp_info

    async def _get_cisco_bgp_info(self) -> Optional[SparseWalkResponse]:
        variables = (
            "cbgpPeer2State",
            "cbgpPeer2AdminStatus",
            "cbgpPeer2RemoteAs",
            "cbgpPeer2FsmEstablishedTime",
        )

        cisco_bgp_info = await self._get_bgp_info(mib_name="CISCO-BGP4-MIB", variables=variables)

        if not cisco_bgp_info:
            return None

        for oid, result in cisco_bgp_info.items():
            result["cbgpPeer2RemoteAddr"] = oid

        cisco_bgp_info = self._transform_variables_from_specific_to_general(
            bgp_info=cisco_bgp_info, bgp_style=BGPStyle.CISCO
        )

        return cisco_bgp_info

    async def _get_general_bgp_info(self) -> Optional[SparseWalkResponse]:
        variables = (
            "bgpPeerState",
            "bgpPeerAdminStatus",
            "bgpPeerRemoteAddr",
            "bgpPeerRemoteAs",
            "bgpPeerFsmEstablishedTime",
        )

        general_bgp_info = await self._get_bgp_info(mib_name="BGP4-MIB", variables=variables)

        if not general_bgp_info:
            return None

        general_bgp_info = self._transform_variables_from_specific_to_general(
            bgp_info=general_bgp_info, bgp_style=BGPStyle.GENERAL
        )

        return general_bgp_info

    async def _get_bgp_info(self, mib_name: str, variables: Iterable[str]) -> Optional[SparseWalkResponse]:
        bgp_info = await self.snmp.sparsewalk(
            *((mib_name, var) for var in variables),
            max_repetitions=3,
        )

        cleaned_bgp_info = dict()

        for oid, entry in bgp_info.items():
            if len(oid) == 1:
                cleaned_bgp_info[oid[0].prettyPrint()] = entry
            else:
                cleaned_bgp_info[oid[1].prettyPrint()] = entry

        return cleaned_bgp_info

    def _transform_variables_from_specific_to_general(
        self, bgp_info: SparseWalkResponse, bgp_style: BGPStyle
    ) -> SparseWalkResponse:
        if bgp_style == BGPStyle.JUNIPER:
            translation = JUNIPER_TRANSLATION_MAP
        elif bgp_style == BGPStyle.CISCO:
            translation = CISCO_TRANSLATION_MAP
        elif bgp_style == BGPStyle.GENERAL:
            translation = GENERAL_TRANSLATION_MAP

        generalized_bgp_info = {key: {} for key in bgp_info.keys()}

        for oid, result in bgp_info.items():
            missing_variables = []
            for general_name, specific_name in translation:
                try:
                    generalized_bgp_info[oid][general_name] = result[specific_name]
                except KeyError:
                    missing_variables.append(specific_name)

        if missing_variables:
            _logger.info(f"router {self.device.name} misses BGP variables ({missing_variables})")
            return None

        return generalized_bgp_info

    def _fixup_ip_addresses(self, bgp_info: SparseWalkResponse) -> SparseWalkResponse:
        fixed_bgp_info = dict()
        for oid, result in bgp_info.items():
            try:
                fixed_remote_address = self._fixup_ip_address(address=result["peer_remote_address"])
            except ValueError:
                _logger.debug(f"{self.device_state.name}: Invalid peer_remote_address {result['peer_remote_address']}")
                continue

            fixed_bgp_info[oid] = result
            fixed_bgp_info[oid]["peer_remote_address"] = fixed_remote_address

        return fixed_bgp_info

    def _fixup_ip_address(self, address: str) -> IPAddress:
        if address.startswith("0x"):
            if len(address) == 10:
                # IPv4 address
                address_str = ".".join((map(str, OctetString(hexValue=address[2:]).asNumbers())))
            elif len(address) == 34:
                # IPv6 address
                address_str = ":".join(["".join(item) for item in zip(*[iter(address[2:])] * 4)])
            else:
                raise ValueError(f"Input {address} could not be converted to IP address.")
        else:
            address_str = address

        return ip_address(address=address_str)

    def _update_single_bgp_entry(self, row: dict[str, Any], local_as: int, uptime: int):
        data = BaseBGPRow(**row)
        if data.peer_remote_address in BUGGY_REMOTE_ADDRESSES:
            return

        # Internal bgp sessions are not observed
        if local_as == data.peer_remote_as:
            return

        if data.peer_state == BGPOperState.ESTABLISHED:
            self._update_established_peer(data, uptime)
        else:
            self._update_nonestablished_peer(data, uptime)

        # Update device state with BGP session
        self.device_state.bgp_peers[data.peer_remote_address] = BGPPeerSession(
            uptime=data.peer_fsm_established_time, admin_status=data.peer_admin_status, oper_state=data.peer_state
        )

    def _update_established_peer(self, data: BaseBGPRow, uptime: int):
        saved_bgp_peer_session = self.device_state.bgp_peers.get(data.peer_remote_address)
        if saved_bgp_peer_session and uptime >= saved_bgp_peer_session.uptime > data.peer_fsm_established_time:
            self._bgp_external_reset(data)
            _logger.debug(f"Noted external reset for {self.device_state.name}: {data.peer_remote_address}")
        else:
            event = self.state.events.get(self.device.name, data.peer_remote_address, BGPEvent)
            if event and event.bgpos != "established":
                self._bgp_external_reset(data)
                _logger.debug(f"BGP session up for {self.device_state.name}: {data.peer_remote_address}")

    def _update_nonestablished_peer(self, data: BaseBGPRow, uptime: int):
        saved_bgp_peer_session = self.device_state.bgp_peers.get(data.peer_remote_address)
        if data.peer_admin_status in ["stop", "halted"]:
            if not saved_bgp_peer_session or saved_bgp_peer_session.admin_status != data.peer_admin_status:
                self._bgp_admin_down(data)
                _logger.debug(
                    f"Router {self.device_state.name} peer {data.peer_remote_address} AS {data.peer_remote_as} "
                    f"admin-down"
                )
        else:
            self._update_peer_with_admin_status_start_or_running(data, saved_bgp_peer_session, uptime)

    def _update_peer_with_admin_status_start_or_running(
        self, data: BaseBGPRow, saved_bgp_peer_session: BGPPeerSession, uptime: int
    ):
        if not saved_bgp_peer_session or saved_bgp_peer_session.admin_status != data.peer_admin_status:
            self._bgp_admin_up(data)
        if not saved_bgp_peer_session or saved_bgp_peer_session.oper_state == "established":
            # First verify that we've been up longer than the required time before we flag it as an alert
            if uptime > TIME_BEFORE_OPER_DOWN_ALERT:
                self._bgp_oper_down(data)
                _logger.debug(
                    f"Router {self.device_state.name} peer {data.peer_remote_address} AS {data.peer_remote_as} "
                    f"is {data.peer_state} (down)",
                )
            else:
                _logger.debug(
                    f"Router {self.device_state.name} peer {data.peer_remote_address} AS {data.peer_remote_as} "
                    f"is {data.peer_state} (down), but uptime = {uptime}",
                )

    def _bgp_external_reset(self, data: BaseBGPRow):
        event = self.state.events.get_or_create_event(self.device.name, data.peer_remote_address, BGPEvent)
        event = self._update_bgp_event(event=event, data=data, last_event="peer was reset (now up)")

        log = f"{event.router} peer {data.peer_remote_address} AS {data.peer_remote_as} was reset (now up)"
        _logger.info(log)
        event.add_log(log)

        self.state.events.commit(event=event)

    def _bgp_admin_down(self, data: BaseBGPRow):
        event = self.state.events.get_or_create_event(self.device.name, data.peer_remote_address, BGPEvent)

        if event.admin_status == data.peer_admin_status:
            return

        copied_data = replace(data, peer_state="down", peer_fsm_established_time=0)
        event = self._update_bgp_event(event=event, data=copied_data, last_event="peer is admin turned off")

        log = (
            f"{event.router} peer {data.peer_remote_address} AS {data.peer_remote_as} is admin turned off "
            f"({data.peer_admin_status})"
        )
        _logger.info(log)
        event.add_log(log)

        self.state.events.commit(event=event)

    def _bgp_admin_up(self, data: BaseBGPRow):
        event = self.state.events.get_or_create_event(self.device.name, data.peer_remote_address, BGPEvent)

        # No previous event, so no need to notify or event already up to date
        if event.id is None or event.admin_status == data.peer_admin_status:
            return

        copied_data = replace(data, peer_fsm_established_time=0)
        event = self._update_bgp_event(event=event, data=copied_data, last_event="peer is now admin turned on")

        log = (
            f"{event.router} peer {data.peer_remote_address} AS {data.peer_remote_as} is now admin turned on "
            f"({data.peer_admin_status})"
        )
        _logger.info(log)
        event.add_log(log)

        self.state.events.commit(event=event)

    def _bgp_oper_down(self, data: BaseBGPRow):
        event = self.state.events.get_or_create_event(self.device.name, data.peer_remote_address, BGPEvent)

        if event.bgpos == "down":
            return

        copied_data = replace(data, peer_state="down")
        event = self._update_bgp_event(event=event, data=copied_data, last_event="peer is down")

        log = (
            f"{event.router} peer {data.peer_remote_address} AS {data.peer_remote_as} is down "
            f"({data.peer_admin_status})"
        )
        _logger.info(log)
        event.add_log(log)

        self.state.events.commit(event=event)

    def _update_bgp_event(self, event: BGPEvent, data: BaseBGPRow, last_event: str) -> BGPEvent:
        """Updates a given BGP event with the given BGP data"""

        event.bgpos = data.peer_state
        event.admin_status = data.peer_admin_status
        event.remote_addr = data.peer_remote_address
        event.remote_as = data.peer_remote_as
        event.peer_uptime = data.peer_fsm_established_time
        event.polladdr = self.device.address
        event.priority = self.device.priority
        event.lastevent = last_event

        return event
