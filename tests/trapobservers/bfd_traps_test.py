import ipaddress
import logging
from unittest.mock import AsyncMock, Mock

import pytest

from zino.config.models import PollDevice
from zino.oid import OID
from zino.state import ZinoState
from zino.statemodels import BFDSessState, Port
from zino.trapd.base import TrapMessage, TrapOriginator
from zino.trapobservers.bfd_traps import BFDTrapObserver


class TestBFDTrapObserver:
    async def test_when_bfd_trap_is_received_it_should_poll_all_affected_sessions(
        self, bfd_session_down_trap, monkeypatch
    ):
        device = bfd_session_down_trap.agent.device
        polldevs_dict = {device.name: PollDevice(name=device.name, address=ipaddress.IPv4Address("127.0.0.1"))}
        bfdtask_run = AsyncMock()
        monkeypatch.setattr("zino.tasks.bfdtask.BFDTask.run", bfdtask_run)

        observer = BFDTrapObserver(state=Mock(), polldevs=polldevs_dict)
        await observer.handle_trap(trap=bfd_session_down_trap)

        assert bfdtask_run.call_count == 4

    async def test_when_bfd_trap_has_been_handled_then_its_snmp_session_should_be_closed(
        self, bfd_session_down_trap, monkeypatch
    ):
        device = bfd_session_down_trap.agent.device
        polldevs_dict = {device.name: PollDevice(name=device.name, address=ipaddress.IPv4Address("127.0.0.1"))}
        used_sessions = []

        async def run_and_open_session(task, session_index=None):
            # Any SNMP request implicitly opens the session, like this:
            task.snmp.open()
            used_sessions.append(task.snmp)

        monkeypatch.setattr("zino.tasks.bfdtask.BFDTask.run", run_and_open_session)

        observer = BFDTrapObserver(state=Mock(), polldevs=polldevs_dict)
        await observer.handle_trap(trap=bfd_session_down_trap)

        assert used_sessions
        assert not any(session._is_open for session in used_sessions)

    async def test_when_polldevs_config_is_missing_it_should_do_nothing(self, bfd_session_down_trap, monkeypatch):
        bfdtask_run = AsyncMock()
        monkeypatch.setattr("zino.tasks.bfdtask.BFDTask.run", bfdtask_run)

        observer = BFDTrapObserver(state=Mock(), polldevs={})
        await observer.handle_trap(trap=bfd_session_down_trap)

        assert bfdtask_run.call_count == 0

    async def test_when_malformed_bfd_trap_is_received_it_should_log_and_return(
        self,
        malformed_bfd_session_down_trap,
        monkeypatch,
        caplog,
    ):
        device = malformed_bfd_session_down_trap.agent.device
        polldevs_dict = {device.name: PollDevice(name=device.name, address=ipaddress.IPv4Address("127.0.0.1"))}
        bfdtask_run = AsyncMock()
        monkeypatch.setattr("zino.tasks.bfdtask.BFDTask.run", bfdtask_run)

        observer = BFDTrapObserver(state=Mock(), polldevs=polldevs_dict)
        with caplog.at_level(logging.INFO):
            await observer.handle_trap(trap=malformed_bfd_session_down_trap)
            assert "malformed" in caplog.text

        assert bfdtask_run.call_count == 0

    async def test_when_trap_range_has_a_missing_index_then_later_sessions_should_still_be_updated(
        self, bfd_trap_with_missing_index, juniper_bfd_state, juniper_bfd_polldev
    ):
        polldevs_dict = {juniper_bfd_polldev.name: juniper_bfd_polldev}

        observer = BFDTrapObserver(state=juniper_bfd_state, polldevs=polldevs_dict)
        await observer.handle_trap(trap=bfd_trap_with_missing_index)

        port = juniper_bfd_state.devices.get(juniper_bfd_polldev.name).ports[1]
        assert port.bfd_state.session_state == BFDSessState.UP


@pytest.fixture
def bfd_trap_with_missing_index(juniper_bfd_state, juniper_bfd_polldev) -> TrapMessage:
    """Returns a BFD session-up trap for a range of two sessions, where only the last one exists on the device"""
    device = juniper_bfd_state.devices.get(juniper_bfd_polldev.name)
    agent = TrapOriginator(address=juniper_bfd_polldev.address, port=162, device=device)
    trap = TrapMessage(agent=agent, mib="BFD-STD-MIB", name="bfdSessUp")
    trap.variables = [
        Mock(var="bfdSessDiag", instance=OID(".4523"), value="noDiagnostic"),
        Mock(var="bfdSessDiag", instance=OID(".4524"), value="noDiagnostic"),
    ]
    return trap


@pytest.fixture
def juniper_bfd_state(juniper_bfd_polldev) -> ZinoState:
    """Returns a state with a Juniper device whose port matches BFD session 4524 in the juniper-bfd-up simulation"""
    state = ZinoState()
    device = state.devices.get(device_name=juniper_bfd_polldev.name)
    device.enterprise_id = 2636
    device.ports[1] = Port(ifindex=1, ifdescr="xe-1/2/0.0")
    return state


@pytest.fixture
def juniper_bfd_polldev(snmpsim, snmp_test_port) -> PollDevice:
    return PollDevice(
        name="buick.lab.example.org", address="127.0.0.1", port=snmp_test_port, community="juniper-bfd-up"
    )


@pytest.fixture
def bfd_session_down_trap(localhost_trap_originator) -> TrapMessage:
    """Returns a correct BFD session-down trap for 4 sessions, with internal state to match"""
    trap = TrapMessage(agent=localhost_trap_originator, mib="BGP4-V2-MIB-JUNIPER", name="bfdSessDown")
    trap.variables = [
        Mock(var="bfdSessDiag", instance=OID(".42"), value="pathDown"),
        Mock(var="bfdSessDiag", instance=OID(".45"), value="pathDown"),
    ]
    return trap


@pytest.fixture
def malformed_bfd_session_down_trap(localhost_trap_originator) -> TrapMessage:
    """Returns a BFD session-down trap with only a single bfdSessDiag value"""
    trap = TrapMessage(agent=localhost_trap_originator, mib="BGP4-V2-MIB-JUNIPER", name="bfdSessDown")
    trap.variables = [
        Mock(var="bfdSessDiag", instance=OID(".42"), value="pathDown"),
    ]
    return trap
