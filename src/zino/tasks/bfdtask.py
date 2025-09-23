import logging
from typing import Dict, Sequence

from zino.oid import OID
from zino.scheduler import get_scheduler
from zino.snmp.base import SparseWalkResponse
from zino.statemodels import BFDEvent, BFDSessState, BFDState, IPAddress, Port
from zino.tasks.task import Task
from zino.utils import reverse_dns

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

    async def run(self, session_index: int = None):
        """Polls data for all BFD sessions.  If session_index is provided, only that session is polled."""
        msg = f" for session index {session_index}" if session_index is not None else ""
        _log.debug("%s: polling BFD data%s", self.device.name, msg)
        if self.device_state.is_juniper:
            polled_state = await self._poll_juniper(session_index)
            await self._update_state_for_all_ports_juniper(polled_state)
        elif self.device_state.is_cisco:
            polled_state = await self._poll_cisco(session_index)
            await self._update_state_for_all_ports_cisco(polled_state)

    async def _update_state_for_all_ports_juniper(self, polled_state: DescrBFDStates):
        for port in self.device_state.ports.values():
            new_state = polled_state.get(port.ifdescr)
            if new_state:
                await self._update_state(port, new_state)

    async def _update_state_for_all_ports_cisco(self, polled_state: IndexBFDStates):
        for port in self.device_state.ports.values():
            new_state = polled_state.get(port.ifindex)
            if new_state:
                await self._update_state(port, new_state)

    async def _update_state(self, port: Port, new_state: BFDState):
        """Updates the BFD state for a port. Will create or update BFD events depending on the state changes"""
        if port.bfd_state:
            if port.bfd_state.session_state != new_state.session_state:
                await self._create_or_update_event(port, new_state)
        elif new_state.session_state != BFDSessState.UP:
            await self._create_or_update_event(port, new_state)

        port.bfd_state = new_state

    async def _create_or_update_event(self, port: Port, new_state: BFDState):
        neigh_rnds = None
        if new_state.session_addr:
            neigh_rnds = await reverse_dns(str(new_state.session_addr))

        event = self.state.events.get_or_create_event(self.device.name, port.ifindex, BFDEvent)

        event.ifindex = port.ifindex
        event.polladdr = self.device.address
        event.priority = self.device.priority
        event.bfdstate = new_state.session_state
        event.bfdix = new_state.session_index
        event.bfddiscr = new_state.session_discr
        event.bfdaddr = new_state.session_addr
        event.neigh_rdns = neigh_rnds

        log = f"changed BFD state to {new_state.session_state} on port {port.ifdescr}"
        event.lastevent = log
        event.add_log(f"Port {port.ifdescr} " + log)
        self.state.events.commit(event)

    async def _poll_juniper(self, session_index: int = None) -> DescrBFDStates:
        if session_index is None:
            bfd_rows = await self.snmp.sparsewalk(*self.JUNIPER_BFD_COLUMNS)
        else:
            bfd_rows = await self._get_single_row(session_index, *self.JUNIPER_BFD_COLUMNS)

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

    async def _poll_cisco(self, session_index: int = None) -> IndexBFDStates:
        if session_index is None:
            bfd_rows = await self.snmp.sparsewalk(*self.CISCO_BFD_COLUMNS)
        else:
            bfd_rows = self._get_single_row(session_index, *self.CISCO_BFD_COLUMNS)

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

    async def _get_single_row(self, session_index: int, *variables: Sequence[str]) -> SparseWalkResponse:
        """Fetches a single row of BFD data for a specific session index using SNMP-GET, and returns a simulated
        SparseWalkResponse for the single row.
        """
        columns = [var + (session_index,) for var in variables]
        response = await self.snmp.get2(*columns)
        row = {var.object: val for var, val in response}
        return {OID((session_index,)): row}

    def _parse_row(self, index: OID, state: str, discr: int, addr: IPAddress) -> BFDState:
        # convert from OID object to int
        session_index = int(index[0])
        bfd_state = BFDState(
            session_state=BFDSessState(state),
            session_index=session_index,
            session_discr=discr,
            session_addr=addr,
        )
        return bfd_state
