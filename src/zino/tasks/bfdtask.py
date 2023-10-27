import ipaddress
import logging
from typing import Dict, Literal

from zino.oid import OID
from zino.scheduler import get_scheduler
from zino.snmp import SNMP, SparseWalkResponse
from zino.statemodels import (
    BFDEvent,
    BFDSessState,
    BFDState,
    EventState,
    IPAddress,
    Port,
)
from zino.tasks.task import Task

_log = logging.getLogger(__name__)

DescrBFDStates = Dict[str, BFDState]
IndexBFDStates = Dict[int, BFDState]


class BFDTask(Task):
    JUNIPER_BFD_COLUMNS = [
        ("BFD-STD-MIB", "bfdSessState"),
        ("JUNIPER-BFD-MIB", "jnxBfdSessIntfName"),  # This should match IfDescr from the IF-MIB
        ("BFD-STD-MIB", "bfdSessDiscriminator"),
        ("BFD-STD-MIB", "bfdSessAddr"),
        ("BFD-STD-MIB", "bfdSessAddrType"),
    ]

    CISCO_BFD_COLUMNS = [
        ("CISCO-IETF-BFD-MIB", "ciscoBfdSessState"),
        ("CISCO-IETF-BFD-MIB", "ciscoBfdSessInterface"),  # This should match IfIndex from the IF-MIB
        ("CISCO-IETF-BFD-MIB", "ciscoBfdSessDiscriminator"),
        ("CISCO-IETF-BFD-MIB", "ciscoBfdSessAddr"),
        ("CISCO-IETF-BFD-MIB", "ciscoBfdSessAddrType"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._scheduler = get_scheduler()
        self._snmp = SNMP(self.device)

    async def run(self):
        if self.device_state.is_juniper:
            polled_state = await self._poll_juniper()
            self._update_state_for_all_ports_juniper(polled_state)
        elif self.device_state.is_cisco:
            polled_state = await self._poll_cisco()
            self._update_state_for_all_ports_cisco(polled_state)

    def _update_state_for_all_ports_juniper(self, polled_state: DescrBFDStates):
        for port in self.device_state.ports.values():
            new_state = polled_state.get(port.ifdescr, BFDState(session_state=BFDSessState.NO_SESSION))
            self._update_state(port, new_state)

    def _update_state_for_all_ports_cisco(self, polled_state: IndexBFDStates):
        for port in self.device_state.ports.values():
            new_state = polled_state.get(port.ifindex, BFDState(session_state=BFDSessState.NO_SESSION))
            self._update_state(port, new_state)

    def _update_state(self, port: Port, new_state: BFDState):
        """Updates the BFD state for a port. Will create or update BFD events depending on the state changes"""
        # Do not create event if this is the first time BFD state is polled for this port
        if port.bfd_state:
            if port.bfd_state.session_state != new_state.session_state:
                self._create_or_update_event(port, new_state)
        port.bfd_state = new_state

    def _create_or_update_event(self, port: Port, new_state: BFDState):
        event, created = self.state.events.get_or_create_event(self.device.name, port.ifindex, BFDEvent)
        if created:
            event.state = EventState.OPEN
            event.add_history("Change state to Open")

        event.bfdstate = new_state.session_state
        event.bfdix = new_state.session_index
        event.bfddiscr = new_state.session_discr
        event.bfdaddr = new_state.session_addr

        log = f"Port {port.ifdescr} changed BFD state from {port.bfd_state.session_state} to {new_state.session_state}"
        event.add_log(log)

    async def _poll_juniper(self) -> DescrBFDStates:
        bfd_rows = await self._snmp.sparsewalk(*self.JUNIPER_BFD_COLUMNS)
        bfd_states = self._parse_juniper_rows(bfd_rows)
        return bfd_states

    def _parse_juniper_rows(self, bfd_rows: SparseWalkResponse) -> DescrBFDStates:
        """The keys for the return dict should match the respective interface's IfDescr value"""
        bfd_states = {}
        for index, row in bfd_rows.items():
            interface_name = row["jnxBfdSessIntfName"]
            bfd_state = self._parse_row(
                index,
                row["bfdSessState"],
                row["bfdSessDiscriminator"],
                row["bfdSessAddr"],  # This is a string representing hexadecimals (ex "0x7f000001")
                row["bfdSessAddrType"],
            )
            bfd_states[interface_name] = bfd_state
        return bfd_states

    async def _poll_cisco(self) -> IndexBFDStates:
        bfd_rows = await self._snmp.sparsewalk(*self.CISCO_BFD_COLUMNS)
        bfd_states = self._parse_cisco_rows(bfd_rows)
        return bfd_states

    def _parse_cisco_rows(self, bfd_rows: SparseWalkResponse) -> IndexBFDStates:
        """The keys for the return dict should match the respective interface's IfIndex value"""
        bfd_states = {}
        for index, row in bfd_rows.items():
            ifindex = row["ciscoBfdSessInterface"]
            bfd_state = self._parse_row(
                index,
                row["ciscoBfdSessState"],
                row["ciscoBfdSessDiscriminator"],
                row["ciscoBfdSessAddr"],  # This is a string representing hexadecimals (ex "0x7f000001")
                row["ciscoBfdSessAddrType"],
            )
            bfd_states[ifindex] = bfd_state
        return bfd_states

    def _parse_row(self, index: OID, state: str, discr: int, addr: str, addr_type: str) -> BFDState:
        try:
            stripped_hexstring = addr.replace("0x", "")
            addr_bytes = bytes.fromhex(stripped_hexstring)
            ipaddr = self._convert_address(addr_bytes, addr_type)
        except ValueError as e:
            _log.error(f"Error converting addr {addr} to an IP address on device {self.device.name}: {e}")
            ipaddr = None

        # convert from OID object to int
        session_index = int(index[0])
        bfd_state = BFDState(
            session_state=BFDSessState(state),
            session_index=session_index,
            session_discr=discr,
            session_addr=ipaddr,
        )
        return bfd_state

    @classmethod
    def _convert_address(cls, address: bytes, address_type: Literal["ipv4", "ipv6"]) -> IPAddress:
        """Converts bytes to either an ipv4 or ipv6 address"""
        if address_type == "ipv4":
            return ipaddress.IPv4Address(address)
        elif address_type == "ipv6":
            return ipaddress.IPv6Address(address)
        else:
            raise ValueError("address_type must be either ipv4 or ipv6")
