import asyncio
import ipaddress
import logging
import shutil
from collections import Counter
from unittest.mock import Mock, patch

import pytest
import pytest_asyncio

from zino.oid import OID
from zino.state import ZinoState
from zino.statemodels import DeviceState
from zino.trapd import (
    TrapMessage,
    TrapObserver,
    TrapOriginator,
    TrapReceiver,
    TrapVarBind,
)

OID_COLD_START = ".1.3.6.1.6.3.1.1.5.1"
OID_SYSNAME_0 = ".1.3.6.1.2.1.1.5.0"


class TestTrapReceiver:
    def test_add_community_should_accept_same_community_multiple_times(self):
        receiver = TrapReceiver()
        receiver.add_community("public")
        receiver.add_community("public")
        assert len(receiver._communities) == 1

    @pytest.mark.asyncio
    async def test_when_trap_lacks_trap_oid_it_should_be_ignored(self, localhost_receiver):
        trap = TrapMessage(agent=TrapOriginator(address=ipaddress.ip_address("127.0.0.1"), port=666))
        trap.variables["sysUpTime"] = TrapVarBind(
            oid=OID(".1.3.6.1.2.1.1.3.0"),
            mib="SNMPv2-MIB",
            var="sysUpTime",
            instance=OID(".0"),
            raw_value=None,
            value=123,
        )
        assert not TrapReceiver._verify_trap(trap)

    @pytest.mark.asyncio
    async def test_when_trap_lacks_sysuptime_it_should_be_ignored(self, localhost_receiver):
        trap = TrapMessage(agent=TrapOriginator(address=ipaddress.ip_address("127.0.0.1"), port=666))
        trap.variables["snmpTrapOID"] = TrapVarBind(
            oid=OID(".1.3.6.1.6.3.1.1.4.1"),
            mib="SNMPv2-MIB",
            var="snmpTrapOID",
            instance=None,
            raw_value=OID(".1.1.1"),
            value=("FAKE-MIB", "fakeTrap"),
        )
        assert not TrapReceiver._verify_trap(trap)

    @pytest.mark.asyncio
    async def test_when_trap_observer_wants_no_traps_auto_subscribe_should_ignore_it(self, localhost_receiver):
        class MockObserver(TrapObserver):
            WANTED_TRAPS = set()

        localhost_receiver.auto_subscribe_observers()
        assert not any(isinstance(observer, MockObserver) for observer in localhost_receiver._observers.values())

    @pytest.mark.asyncio
    async def test_when_called_multiple_times_auto_subscribe_should_not_add_duplicates(self, localhost_receiver):
        """The same observer class should not be subscribed more than once for the same trap"""

        class MockObserver(TrapObserver):
            WANTED_TRAPS = {("MOCK-MIB", "mockTrap")}

        localhost_receiver.auto_subscribe_observers()
        localhost_receiver.auto_subscribe_observers()

        type_counts = Counter(
            (trap, type(observer))
            for trap, observers in localhost_receiver._observers.items()
            for observer in observers
        )
        dupes = {ident: count for ident, count in type_counts.items() if count > 1}
        assert not dupes


@pytest.mark.skipif(not shutil.which("snmptrap"), reason="Cannot find snmptrap command line program")
class TestTrapReceiverExternally:
    @pytest.mark.asyncio
    async def test_when_trap_is_from_unknown_device_it_should_ignore_it(self, event_loop, caplog):
        receiver = TrapReceiver(address="127.0.0.1", port=1162, loop=event_loop)
        receiver.add_community("public")
        try:
            await receiver.open()

            with caplog.at_level(logging.DEBUG):
                await send_trap_externally(OID_COLD_START, OID_SYSNAME_0, "s", "'MockDevice'")
                assert "ignored trap from 127.0.0.1" in caplog.text
        finally:
            receiver.close()

    @pytest.mark.asyncio
    async def test_when_trap_is_from_known_device_it_should_log_it(self, localhost_receiver, caplog):
        with caplog.at_level(logging.DEBUG):
            await send_trap_externally(OID_COLD_START, OID_SYSNAME_0, "s", "'MockDevice'")
            assert "Trap from localhost" in caplog.text
            assert OID_COLD_START in caplog.text

    @pytest.mark.asyncio
    async def test_when_observer_is_added_and_trap_matches_it_should_call_it(self, localhost_receiver):
        observer = Mock()
        localhost_receiver.observe(observer, ("SNMPv2-MIB", "coldStart"))
        await send_trap_externally(OID_COLD_START, OID_SYSNAME_0, "s", "'MockDevice'")
        assert observer.handle_trap.called

    @pytest.mark.asyncio
    async def test_when_observer_raises_unhandled_exception_it_should_log_it(self, localhost_receiver, caplog):
        crashing_observer = Mock()
        crashing_observer.handle_trap.side_effect = ValueError("mocked exception")
        localhost_receiver.observe(crashing_observer, ("SNMPv2-MIB", "coldStart"))

        with caplog.at_level(logging.INFO):
            await send_trap_externally(OID_COLD_START, OID_SYSNAME_0, "s", "'MockDevice'")
            assert "ValueError" in caplog.text
            assert "mocked exception" in caplog.text

    @pytest.mark.asyncio
    async def test_when_early_observer_returns_false_it_should_not_call_later_observers(self, localhost_receiver):
        early_observer = Mock()
        early_observer.handle_trap.return_value = False
        late_observer = Mock()
        localhost_receiver.observe(early_observer, ("BGP4-MIB", "bgpBackwardTransition"))
        localhost_receiver.observe(late_observer, ("BGP4-MIB", "bgpBackwardTransition"))
        bgp_backward_transition_trap = [
            ".1.3.6.1.2.1.15.7.2",
            ".1.3.6.1.2.1.15.3.1.7",
            "a",
            "192.168.42.42",
            ".1.3.6.1.2.1.15.3.1.14",
            "x",
            "4242",
            ".1.3.6.1.2.1.15.3.1.2",
            "i",
            "2",
        ]
        await send_trap_externally(*bgp_backward_transition_trap)
        assert early_observer.handle_trap.called
        assert not late_observer.handle_trap.called

    @pytest.mark.asyncio
    async def test_when_conversion_of_varbind_to_python_object_fails_it_should_set_value_to_none(
        self, localhost_receiver
    ):
        with patch("zino.trapd._mib_value_to_python", side_effect=ValueError("mock exception")):
            with patch.object(localhost_receiver, "dispatch_trap") as mock_dispatch:
                await send_trap_externally(OID_COLD_START, OID_SYSNAME_0, "s", "'MockDevice'")
                assert mock_dispatch.called
                trap = mock_dispatch.call_args.args[0]
                assert all(var.value is None for var in trap.variables.values())

    @pytest.mark.asyncio
    async def test_when_trap_verification_fails_it_should_not_dispatch_trap(self, localhost_receiver):
        with patch.object(localhost_receiver, "_verify_trap", return_value=False):
            with patch.object(localhost_receiver, "dispatch_trap") as mock_dispatch:
                await send_trap_externally(OID_COLD_START, OID_SYSNAME_0, "s", "'MockDevice'")
                assert not mock_dispatch.called


@pytest.fixture
def state_with_localhost():
    localhost = ipaddress.ip_address("127.0.0.1")
    state = ZinoState()
    state.devices.devices["localhost"] = DeviceState(name="localhost", addresses={localhost})
    state.addresses[localhost] = "localhost"
    yield state


@pytest_asyncio.fixture
async def localhost_receiver(state_with_localhost, event_loop) -> TrapReceiver:
    """Yields a TrapReceiver instance with a standardized setup for running external tests on localhost"""
    receiver = TrapReceiver(address="127.0.0.1", port=1162, loop=event_loop, state=state_with_localhost)
    receiver.add_community("public")
    await receiver.open()
    yield receiver
    receiver.close()


async def send_trap_externally(*args: str):
    args = " ".join(args)
    proc = await asyncio.create_subprocess_shell(f"snmptrap -v 2c -c public localhost:1162 '' {args}")
    await proc.communicate()
    assert proc.returncode == 0, "snmptrap command exited with error"
