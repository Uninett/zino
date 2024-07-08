import ipaddress
import logging
from unittest.mock import Mock

import pytest

from zino.config.models import PollDevice
from zino.oid import OID
from zino.trapd import TrapMessage
from zino.trapobservers.bfd_traps import BFDTrapObserver


class TestBFDTrapObserver:
    @pytest.mark.asyncio
    async def test_when_bfd_trap_is_received_it_should_poll_all_affected_sessions(
        self, bfd_session_down_trap, monkeypatch, event_loop
    ):
        device = bfd_session_down_trap.agent.device
        polldevs_dict = {device.name: PollDevice(name=device.name, address=ipaddress.IPv4Address("127.0.0.1"))}
        called_future = event_loop.create_future()
        called_future.set_result(None)
        bfdtask_run = Mock(return_value=called_future)
        monkeypatch.setattr("zino.tasks.bfdtask.BFDTask.run", bfdtask_run)

        observer = BFDTrapObserver(state=Mock(), polldevs=polldevs_dict)
        await observer.handle_trap(trap=bfd_session_down_trap)

        assert bfdtask_run.call_count == 4

    @pytest.mark.asyncio
    async def test_when_polldevs_config_is_missing_it_should_do_nothing(
        self, bfd_session_down_trap, monkeypatch, event_loop
    ):
        called_future = event_loop.create_future()
        called_future.set_result(None)
        bfdtask_run = Mock(return_value=called_future)
        monkeypatch.setattr("zino.tasks.bfdtask.BFDTask.run", bfdtask_run)

        observer = BFDTrapObserver(state=Mock(), polldevs={})
        await observer.handle_trap(trap=bfd_session_down_trap)

        assert bfdtask_run.call_count == 0

    @pytest.mark.asyncio
    async def test_when_malformed_bfd_trap_is_received_it_should_log_and_return(
        self,
        malformed_bfd_session_down_trap,
        monkeypatch,
        event_loop,
        caplog,
    ):
        device = malformed_bfd_session_down_trap.agent.device
        polldevs_dict = {device.name: PollDevice(name=device.name, address=ipaddress.IPv4Address("127.0.0.1"))}
        called_future = event_loop.create_future()
        called_future.set_result(None)
        bfdtask_run = Mock(return_value=called_future)
        monkeypatch.setattr("zino.tasks.bfdtask.BFDTask.run", bfdtask_run)

        observer = BFDTrapObserver(state=Mock(), polldevs=polldevs_dict)
        with caplog.at_level(logging.INFO):
            await observer.handle_trap(trap=malformed_bfd_session_down_trap)
            assert "malformed" in caplog.text

        assert bfdtask_run.call_count == 0


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
