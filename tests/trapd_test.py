import asyncio
import ipaddress
import logging
import shutil
from unittest.mock import Mock

import pytest
import pytest_asyncio

from zino.state import ZinoState
from zino.statemodels import DeviceState
from zino.trapd import TrapReceiver

OID_COLD_START = ".1.3.6.1.6.3.1.1.5.1"
OID_SYSNAME_0 = ".1.3.6.1.2.1.1.5.0"


class TestTrapReceiver:
    def test_add_community_should_accept_same_community_multiple_times(self):
        receiver = TrapReceiver()
        receiver.add_community("public")
        receiver.add_community("public")
        assert len(receiver._communities) == 1


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
        assert observer.called

    @pytest.mark.asyncio
    async def test_when_observer_raises_unhandled_exception_it_should_log_it(self, localhost_receiver, caplog):
        crashing_observer = Mock()
        crashing_observer.side_effect = ValueError("mocked exception")
        localhost_receiver.observe(crashing_observer, ("SNMPv2-MIB", "coldStart"))

        with caplog.at_level(logging.INFO):
            await send_trap_externally(OID_COLD_START, OID_SYSNAME_0, "s", "'MockDevice'")
            assert "ValueError" in caplog.text
            assert "mocked exception" in caplog.text

    @pytest.mark.asyncio
    async def test_when_trap_from_ignore_list_is_received_it_should_be_ignored(self, localhost_receiver):
        late_observer = Mock()
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
        assert not late_observer.called


@pytest.fixture
def state_with_localhost():
    localhost = ipaddress.ip_address("127.0.0.1")
    state = ZinoState()
    state.devices.devices["localhost"] = DeviceState(name="localhost", addresses={localhost})
    state.addresses[localhost] = "localhost"
    yield state


@pytest_asyncio.fixture
async def localhost_receiver(state_with_localhost, event_loop):
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
