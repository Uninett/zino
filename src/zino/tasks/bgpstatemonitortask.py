import logging
from dataclasses import dataclass
from ipaddress import AddressValueError, IPv4Address, IPv6Address
from typing import Any, Iterable, Tuple, Union

from pyasn1.type.univ import OctetString

from zino.oid import OID
from zino.snmp import SNMP, MibObject, NoSuchNameError, SparseWalkResponse
from zino.statemodels import (
    BgpAdminStatus,
    BGPEvent,
    BgpOperStatus,
    BgpStyle,
    EventState,
    IPAddress,
)
from zino.tasks.task import Task

_logger = logging.getLogger(__name__)


@dataclass
class BaseBgpRow:
    peer_state: BgpOperStatus
    peer_admin_status: BgpAdminStatus
    peer_remote_address: IPAddress
    peer_remote_as: int
    peer_fsm_established_time: int


class BgpStateMonitorTask(Task):
    """FIXME something useful here"""

    async def run(self):
        bgp_style = await self._get_bgp_style()
        if bgp_style != self.device_state.bgp_style:
            _logger.debug(f"Router {self.device_state.name} wrong BGP style, was '{self.device_state.bgp_style}'")
            self.device_state.bgp_style = bgp_style
        if not bgp_style:
            return

        local_as = await self._get_local_as(bgp_style=bgp_style)
        uptime = await self._get_uptime()
        if not local_as or not uptime:
            return

        if bgp_style == "juniper":
            bgp_info = await self._get_juniper_bgp_info()
        elif bgp_style == "cisco":
            bgp_info = await self._get_cisco_bgp_info()
        elif bgp_style == "general":
            bgp_info = await self._get_general_bgp_info()

        if not bgp_info:
            return

        bgp_info = self._fixup_ip_addresses(bgp_info=bgp_info)

        for oid, result in bgp_info.items():
            self._update_single_bgp_entry(oid, result, local_as, uptime)

    async def _get_bgp_style(self) -> Union[BgpStyle, None]:
        snmp = SNMP(self.device)

        # TODO Should this be moved to the SNMP file?
        def _is_in_scope(local_as: MibObject, oid: Tuple[str, str]):
            object_type = snmp._oid_to_object_type(*oid)
            snmp._resolve_object(object_type=object_type)
            root = OID(object_type[0])
            return root.is_a_prefix_of(other=local_as.oid)

        try:
            juniper_local_as = await snmp.getnext("BGP4-V2-MIB-JUNIPER", "jnxBgpM2")
        except NoSuchNameError:
            pass
        else:
            if juniper_local_as and _is_in_scope(local_as=juniper_local_as, oid=("BGP4-V2-MIB-JUNIPER", "jnxBgpM2")):
                return "juniper"

        try:
            cisco_local_as = await snmp.getnext("CISCO-BGP4-MIB", "cbgpPeer2Table")
        except NoSuchNameError:
            pass
        else:
            if cisco_local_as and _is_in_scope(local_as=cisco_local_as, oid=("CISCO-BGP4-MIB", "cbgpPeer2Table")):
                return "cisco"

        try:
            general_local_as = await snmp.getnext("BGP4-MIB", "bgp")
        except NoSuchNameError:
            pass
        else:
            if general_local_as and _is_in_scope(local_as=general_local_as, oid=("BGP4-MIB", "bgp")):
                return "general"

        return None

    async def _get_local_as(self, bgp_style: BgpStyle) -> Union[int, None]:
        snmp = SNMP(self.device)
        if bgp_style == "juniper":
            # Juniper has multiple entries for this, so we just take the first
            try:
                return (await snmp.getnext("BGP4-V2-MIB-JUNIPER", "jnxBgpM2PeerLocalAs")).value
            except NoSuchNameError:
                _logger.info(f"router {self.device.name} misses jnxBgpM2PeerLocalAs")
                return None
        if bgp_style == "cisco":
            try:
                return (await snmp.get("CISCO-BGP4-MIB", "cbgpLocalAs", 0)).value
            except NoSuchNameError:
                _logger.info(f"router {self.device.name} misses cbgpLocalAs")
                return None
        if bgp_style == "general":
            try:
                return (await snmp.get("BGP4-MIB", "bgpLocalAs", 0)).value
            except NoSuchNameError:
                _logger.info(f"router {self.device.name} misses bgpLocalAs")
                return None

    async def _get_uptime(self) -> Union[int, None]:
        snmp = SNMP(self.device)
        try:
            return (await snmp.get("SNMPv2-MIB", "sysUpTime", 0)).value / 100
        except NoSuchNameError:
            _logger.info(f"router {self.device.name} misses sysUpTime")
            return None

    async def _get_juniper_bgp_info(self) -> Union[SparseWalkResponse, None]:
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
            bgp_info=juniper_bgp_info, bgp_style="juniper"
        )

        return juniper_bgp_info

    async def _get_cisco_bgp_info(self) -> Union[SparseWalkResponse, None]:
        variables = (
            "cbgpPeer2State",
            "cbgpPeer2AdminStatus",
            "cbgpPeer2RemoteAs",
            "cbgpPeer2FsmEstablishedTime",
        )

        cisco_bgp_info = await self._get_bgp_info(mib_name="CISCO-BGP4-MIB", variables=variables)

        for oid, result in cisco_bgp_info.items():
            result["cbgpPeer2RemoteAddr"] = oid

        if not cisco_bgp_info:
            return None

        cisco_bgp_info = self._transform_variables_from_specific_to_general(bgp_info=cisco_bgp_info, bgp_style="cisco")

        return cisco_bgp_info

    async def _get_general_bgp_info(self) -> Union[SparseWalkResponse, None]:
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
            bgp_info=general_bgp_info, bgp_style="general"
        )

        return general_bgp_info

    async def _get_bgp_info(self, mib_name: str, variables: Iterable[str]) -> Union[SparseWalkResponse, None]:
        snmp = SNMP(self.device)
        try:
            bgp_info = await snmp.sparsewalk(
                *((mib_name, var) for var in variables),
                max_repetitions=3,
            )
        except NoSuchNameError as e:
            _logger.info(f"router {self.device.name} misses BGP variables ({e})")
            return None

        cleaned_bgp_info = dict()

        for oid, entry in bgp_info.items():
            if len(oid) == 1:
                cleaned_bgp_info[oid[0].prettyPrint()] = entry
            else:
                cleaned_bgp_info[oid[1].prettyPrint()] = entry

        return cleaned_bgp_info

    def _transform_variables_from_specific_to_general(
        self, bgp_info: SparseWalkResponse, bgp_style: BgpStyle
    ) -> SparseWalkResponse:
        juniper_translation = [
            ("peer_state", "jnxBgpM2PeerState"),
            ("peer_admin_status", "jnxBgpM2PeerStatus"),
            ("peer_remote_address", "jnxBgpM2PeerRemoteAddr"),
            ("peer_remote_as", "jnxBgpM2PeerRemoteAs"),
            ("peer_fsm_established_time", "jnxBgpM2PeerFsmEstablishedTime"),
        ]
        cisco_translation = [
            ("peer_state", "cbgpPeer2State"),
            ("peer_admin_status", "cbgpPeer2AdminStatus"),
            ("peer_remote_address", "cbgpPeer2RemoteAddr"),
            ("peer_remote_as", "cbgpPeer2RemoteAs"),
            ("peer_fsm_established_time", "cbgpPeer2FsmEstablishedTime"),
        ]
        general_translation = [
            ("peer_state", "bgpPeerState"),
            ("peer_admin_status", "bgpPeerAdminStatus"),
            ("peer_remote_address", "bgpPeerRemoteAddr"),
            ("peer_remote_as", "bgpPeerRemoteAs"),
            ("peer_fsm_established_time", "bgpPeerFsmEstablishedTime"),
        ]

        if bgp_style == "juniper":
            translation = juniper_translation
        elif bgp_style == "cisco":
            translation = cisco_translation
        elif bgp_style == "general":
            translation = general_translation

        generalized_bgp_info = {key: {} for key in bgp_info.keys()}

        for oid, result in bgp_info.items():
            for general_name, specific_name in translation:
                generalized_bgp_info[oid][general_name] = result[specific_name]

        return generalized_bgp_info

    def _fixup_ip_addresses(self, bgp_info: SparseWalkResponse) -> SparseWalkResponse:
        fixed_bgp_info = dict()
        for oid, result in bgp_info.items():
            fixed_remote_address = self._fixup_ip_address(address=result["peer_remote_address"])
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
                raise TypeError(f"Input {address} could not be converted to IP address.")
        else:
            address_str = address

        try:
            return IPv4Address(address=address_str)
        except AddressValueError:
            pass
        try:
            return IPv6Address(address=address_str)
        except AddressValueError:
            pass

        raise TypeError(f"Input {address} could not be converted to IP address.")

    def _update_single_bgp_entry(self, oid, row: dict[str, Any], local_as: int, uptime: int):
        data = BaseBgpRow(**row)

        # Bug in JunOS -- info from IPv6 BGP sessions spill over
        if data.peer_remote_address == "0.0.0.0":
            return
        # Bug in earlier Cisco IOS, info from elsewhere (IPv6?) spills over
        if data.peer_remote_address == "32.1.7.0":
            return

        # Internal bgp sessions are not observed
        if local_as == data.peer_remote_as:
            return

        index = f"{self.device.name},{oid}"

        if data.peer_state == "established":
            bgp_peer_up_time = self.device_state.bgp_peer_up_times.get(data.peer_remote_address, None)
            if bgp_peer_up_time and uptime >= bgp_peer_up_time and bgp_peer_up_time > data.peer_fsm_established_time:
                self._bgp_external_reset(data)
                _logger.debug(f"Noted external reset for {self.device_state.name}: {index}")
            else:
                event = self.state.events.get(self.device.name, data.peer_remote_address, BGPEvent)
                if event and event.operational_state != "established":
                    self._bgp_external_reset(data)
                    _logger.debug(f"BGP session up for {self.device_state.name}: {index}")
        else:
            bgp_peer_admin_state = self.device_state.bgp_peer_admin_states.get(data.peer_remote_address, None)
            if not bgp_peer_admin_state:
                self.device_state.bgp_peer_admin_states[data.peer_remote_address] = "unknown"
                bgp_peer_admin_state = "unknown"
            if data.peer_admin_status in ["stop", "halted"]:
                if bgp_peer_admin_state != data.peer_admin_status:
                    self._bgp_admin_down(data)
                    _logger.debug(
                        f"Router {self.device_state.name} peer {data.peer_remote_address} AS {data.peer_remote_as} "
                        f"admin-down"
                    )
            # peer_admin_status is start or running
            else:
                if self.device_state.bgp_peer_admin_states[data.peer_remote_address] != data.peer_admin_status:
                    self._bgp_admin_up(data)
                bgp_peer_oper_state = self.device_state.bgp_peer_oper_states.get(data.peer_remote_address, None)
                # breakpoint()
                if not bgp_peer_oper_state:
                    self.device_state.bgp_peer_oper_states[data.peer_remote_address] = "established"
                    bgp_peer_oper_state = "established"
                if bgp_peer_oper_state == "established":
                    # First verify that we've been up more than 10 minutes before we flag it as an alert
                    if uptime > 600:
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

        # Update all states
        self.device_state.bgp_peer_oper_states[data.peer_remote_address] = data.peer_state
        self.device_state.bgp_peer_admin_states[data.peer_remote_address] = data.peer_admin_status
        self.device_state.bgp_peer_up_times[data.peer_remote_address] = data.peer_fsm_established_time

        # Add new peers if found
        if data.peer_remote_address not in self.device_state.bgp_peers:
            self.device_state.bgp_peers.append(data.peer_remote_address)

    def _bgp_external_reset(self, data: BaseBgpRow):
        event, created = self.state.events.get_or_create_event(self.device.name, data.peer_remote_address, BGPEvent)
        if created:
            event.state = EventState.OPEN
            event.add_history("Change state to Open")

        event.operational_state = data.peer_state
        event.admin_status = data.peer_admin_status
        event.remote_address = data.peer_remote_address
        event.remote_as = data.peer_remote_as
        event.peer_uptime = data.peer_fsm_established_time

        log = f"{event.router} peer {data.peer_remote_address} AS {data.peer_remote_as} was reset (now up)"
        _logger.info(log)
        event.add_log(log)

    def _bgp_admin_down(self, data: BaseBgpRow):
        event, created = self.state.events.get_or_create_event(self.device.name, data.peer_remote_address, BGPEvent)
        if created:
            event.state = EventState.OPEN
            event.add_history("Change state to Open")

        if event.admin_status == data.peer_admin_status:
            return

        event.operational_state = "down"
        event.admin_status = data.peer_admin_status
        event.remote_address = data.peer_remote_address
        event.remote_as = data.peer_remote_as
        event.peer_uptime = 0

        log = (
            f"{event.router} peer {data.peer_remote_address} AS {data.peer_remote_as} is turned off "
            f"({data.peer_admin_status})"
        )
        _logger.info(log)
        event.add_log(log)

    def _bgp_admin_up(self, data: BaseBgpRow):
        event, created = self.state.events.get_or_create_event(self.device.name, data.peer_remote_address, BGPEvent)

        if created:
            event.state = EventState.OPEN
            event.add_history("Change state to Open")

        if event.admin_status == data.peer_admin_status:
            return

        event.operational_state = data.peer_state
        event.admin_status = data.peer_admin_status
        event.remote_address = data.peer_remote_address
        event.remote_as = data.peer_remote_as
        event.peer_uptime = 0

        log = (
            f"{event.router} peer {data.peer_remote_address} AS {data.peer_remote_as} is now turned on "
            f"({data.peer_admin_status})"
        )
        _logger.info(log)
        event.add_log(log)

    def _bgp_oper_down(self, data: BaseBgpRow):
        event, created = self.state.events.get_or_create_event(self.device.name, data.peer_remote_address, BGPEvent)
        if created:
            event.state = EventState.OPEN
            event.add_history("Change state to Open")

        if event.operational_state == "down":
            return

        event.operational_state = "down"
        event.admin_status = data.peer_admin_status
        event.remote_address = data.peer_remote_address
        event.remote_as = data.peer_remote_as
        event.peer_uptime = data.peer_fsm_established_time

        log = (
            f"{event.router} peer {data.peer_remote_address} AS {data.peer_remote_as} is down "
            f"({data.peer_admin_status})"
        )
        _logger.info(log)
        event.add_log(log)
