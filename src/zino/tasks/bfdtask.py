import ipaddress
import logging
from typing import Dict, Literal

from zino.scheduler import get_scheduler
from zino.snmp import SNMP, SparseWalkResponse
from zino.statemodels import BFDEvent, BFDSessState, BFDState, IPAddress, Port
from zino.tasks.task import Task

_log = logging.getLogger(__name__)

BFDStates = Dict[str, BFDState]


class BFDTask(Task):
    JUNIPER_BFD_COLUMNS = [
        ("BFD-STD-MIB", "bfdSessState"),
        ("JUNIPER-BFD-MIB", "jnxBfdSessIntfName"),  # This should match IfDescr from the IF-MIB
        ("BFD-STD-MIB", "bfdSessDiscriminator"),
        ("BFD-STD-MIB", "bfdSessAddr"),
        ("BFD-STD-MIB", "bfdSessAddrType"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._scheduler = get_scheduler()
        self._snmp = SNMP(self.device)

    async def run(self):
        if self.device_state.is_juniper:
            polled_state = await self._poll_juniper()
            self._update_state_for_all_ports(polled_state)

    def _update_state_for_all_ports(self, polled_state: BFDStates):
        for port in self.device_state.ports.values():
            new_state = polled_state.get(port.ifdescr, BFDState(session_state=BFDSessState.NO_SESSION))
            self._update_state(port, new_state)

    def _update_state(self, port: Port, new_state: BFDState):
        """Updates the BFD state for a port. Will create or update BFD events depending on the state changes"""
        # Do not create event if this is the first time BFD state is polled for this port
        if port.bfd_state:
            if port.bfd_state.session_state != new_state.session_state:
                self._create_or_update_event(port, new_state)
        port.bfd_state = new_state

    def _create_or_update_event(self, port: Port, new_state: BFDState):
        event = self.state.events.get_or_create_event(self.device.name, port.ifindex, BFDEvent)

        event.bfdstate = new_state.session_state
        event.bfdix = new_state.session_index
        event.bfddiscr = new_state.session_discr
        event.bfdaddr = new_state.session_addr

        log = f"Port {port.ifdescr} changed BFD state from {port.bfd_state.session_state} to {new_state.session_state}"
        event.add_log(log)
        self.state.events.commit(event)

    async def _poll_juniper(self) -> BFDStates:
        bfd_rows = await self._snmp.sparsewalk(*self.JUNIPER_BFD_COLUMNS)
        bfd_states = self._parse_juniper_rows(bfd_rows)
        return bfd_states

    def _parse_juniper_rows(self, bfd_rows: SparseWalkResponse) -> BFDStates:
        """The keys for the return dict should match the respective interface's IfDescr value"""
        bfd_states = {}
        for index, row in bfd_rows.items():
            interface_name = row["jnxBfdSessIntfName"]
            session_state = row["bfdSessState"]
            session_discr = row["bfdSessDiscriminator"]
            session_addr = row["bfdSessAddr"]  # This is a string representing hexadecimals (ex 0x7f000001)
            session_addr_type = row["bfdSessAddrType"]

            try:
                stripped_hexstring = session_addr.replace("0x", "")
                addr_bytes = bytes.fromhex(stripped_hexstring)
                ipaddr = self._convert_address(addr_bytes, session_addr_type)
            except ValueError as e:
                _log.error(f"Error converting bfdSessAddr object to an IP address on device {self.device.name}: {e}")
                ipaddr = None

            # convert from OID object to int
            session_index = int(index[0])
            bfd_state = BFDState(
                session_state=BFDSessState(session_state),
                session_index=session_index,
                session_discr=session_discr,
                session_addr=ipaddr,
            )
            bfd_states[interface_name] = bfd_state
        return bfd_states

    @classmethod
    def _convert_address(cls, address: bytes, address_type: Literal["ipv4", "ipv6"]) -> IPAddress:
        """Converts bytes to either an ipv4 or ipv6 address"""
        if address_type == "ipv4":
            return ipaddress.IPv4Address(address)
        elif address_type == "ipv6":
            return ipaddress.IPv6Address(address)
        else:
            raise ValueError("address_type must be either ipv4 or ipv6")
