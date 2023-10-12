import logging
from typing import Dict

from zino.scheduler import get_scheduler
from zino.snmp import SNMP, SparseWalkResponse
from zino.statemodels import (
    BFDEvent,
    BFDSessState,
    BFDState,
    DeviceState,
    EventState,
    Port,
)
from zino.tasks.task import Task

_log = logging.getLogger(__name__)

BFDStates = Dict[str, BFDState]


class BFDTask(Task):
    JUNIPER_BFD_COLUMNS = [
        ("BFD-STD-MIB", "bfdSessState"),
        ("JUNIPER-BFD-MIB", "jnxBfdSessIntfName"),  # This should match IfDescr from the IF-MIB
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._scheduler = get_scheduler()
        self._snmp = SNMP(self.device)

    async def run(self):
        if self._device_state.is_juniper:
            polled_state = await self._poll_juniper()
            self._update_state_for_all_ports(polled_state)

    def _update_state_for_all_ports(self, polled_state: BFDStates):
        for port in self._device_state.ports.values():
            new_state = polled_state.get(port.ifdescr, BFDState(session_state=BFDSessState.NOSESSION))
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

        event.session_index = new_state.session_index
        event.session_state = new_state.session_state
        event.ifindex = port.ifindex

        log = f"Port {port.ifdescr} changed BFD state from {port.bfd_state.session_state} to {new_state.session_state}"
        event.add_log(log)

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
            # convert from OID object to int
            session_index = int(index[0])
            bfd_states[interface_name] = BFDState(
                session_state=BFDSessState(session_state),
                session_index=session_index,
            )
        return bfd_states

    @property
    def _device_state(self) -> DeviceState:
        return self.state.devices.get(self.device.name)
