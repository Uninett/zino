import logging
from typing import Dict

from zino.oid import OID
from zino.scheduler import get_scheduler
from zino.snmp import SparseWalkResponse
from zino.statemodels import BFDEvent, BFDSessState, BFDState, Port
from zino.tasks.task import Task
from zino.utils import parse_ip

_log = logging.getLogger(__name__)

# IfDescr as key
DescrBFDStates = Dict[str, BFDState]
# IfIndex as key
IndexBFDStates = Dict[int, BFDState]


class BFDTask(Task):
    JUNIPER_BFD_COLUMNS = [
        ("BFD-STD-MIB", "bfdSessState"),
        ("JUNIPER-BFD-MIB", "jnxBfdSessIntfName"),  # This should match IfDescr from the IF-MIB
        ("BFD-STD-MIB", "bfdSessDiscriminator"),
        ("BFD-STD-MIB", "bfdSessAddr"),
    ]

    CISCO_BFD_COLUMNS = [
        ("CISCO-IETF-BFD-MIB", "ciscoBfdSessState"),
        ("CISCO-IETF-BFD-MIB", "ciscoBfdSessInterface"),  # This should match IfIndex from the IF-MIB
        ("CISCO-IETF-BFD-MIB", "ciscoBfdSessDiscriminator"),
        ("CISCO-IETF-BFD-MIB", "ciscoBfdSessAddr"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._scheduler = get_scheduler()

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
        event = self.state.events.get_or_create_event(self.device.name, port.ifindex, BFDEvent)

        event.ifindex = port.ifindex
        event.polladdr = self.device.address
        event.priority = self.device.priority
        event.bfdstate = new_state.session_state
        event.bfdix = new_state.session_index
        event.bfddiscr = new_state.session_discr
        event.bfdaddr = new_state.session_addr

        log = f"changed BFD state from {port.bfd_state.session_state} to {new_state.session_state}"
        event.lastevent = log
        event.add_log(f"Port {port.ifdescr}" + log)
        self.state.events.commit(event)

    async def _poll_juniper(self) -> DescrBFDStates:
        bfd_rows = await self.snmp.sparsewalk(*self.JUNIPER_BFD_COLUMNS)
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
            )
            bfd_states[interface_name] = bfd_state
        return bfd_states

    async def _poll_cisco(self) -> IndexBFDStates:
        bfd_rows = await self.snmp.sparsewalk(*self.CISCO_BFD_COLUMNS)
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
            )
            bfd_states[ifindex] = bfd_state
        return bfd_states

    def _parse_row(self, index: OID, state: str, discr: int, addr: str) -> BFDState:
        try:
            ipaddr = parse_ip(addr)
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
