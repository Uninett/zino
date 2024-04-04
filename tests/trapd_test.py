import asyncio
import ipaddress
import logging
import shutil
from unittest.mock import Mock

import pytest

from zino.state import ZinoState
from zino.statemodels import DeviceState
from zino.trapd import TrapReceiver


class TestTrapReceiver:
    def test_add_community_should_accept_same_community_multiple_times(self):
        receiver = TrapReceiver()
        receiver.add_community("public")
        receiver.add_community("public")
        assert len(receiver._communities) == 1

    @pytest.mark.skipif(not shutil.which("snmptrap"), reason="Cannot find snmptrap command line program")
    @pytest.mark.asyncio
    async def test_when_trap_is_from_unknown_device_it_should_ignore_it(self, event_loop, caplog):
        receiver = TrapReceiver(address="127.0.0.1", port=1162, loop=event_loop)
        receiver.add_community("public")
        try:
            await receiver.open()

            cold_start = ".1.3.6.1.6.3.1.1.5.1"
            sysname_0 = ".1.3.6.1.2.1.1.5.0"
            with caplog.at_level(logging.DEBUG):
                await send_trap_externally(cold_start, sysname_0, "s", "'MockDevice'")
                assert "ignored trap from 127.0.0.1" in caplog.text
        finally:
            receiver.close()

    @pytest.mark.skipif(not shutil.which("snmptrap"), reason="Cannot find snmptrap command line program")
    @pytest.mark.asyncio
    async def test_when_trap_is_from_known_device_it_should_log_it(self, state_with_localhost, event_loop, caplog):
        receiver = TrapReceiver(address="127.0.0.1", port=1162, loop=event_loop, state=state_with_localhost)
        receiver.add_community("public")
        try:
            await receiver.open()

            cold_start = ".1.3.6.1.6.3.1.1.5.1"
            sysname_0 = ".1.3.6.1.2.1.1.5.0"
            with caplog.at_level(logging.DEBUG):
                await send_trap_externally(cold_start, sysname_0, "s", "'MockDevice'")
                assert "Trap from localhost" in caplog.text
                assert cold_start in caplog.text
        finally:
            receiver.close()

    @pytest.mark.skipif(not shutil.which("snmptrap"), reason="Cannot find snmptrap command line program")
    @pytest.mark.asyncio
    async def test_when_observer_is_added_and_trap_matches_it_should_call_it(self, state_with_localhost, event_loop):
        receiver = TrapReceiver(address="127.0.0.1", port=1162, loop=event_loop, state=state_with_localhost)
        receiver.add_community("public")
        observer = Mock()
        receiver.observe(observer, ("SNMPv2-MIB", "coldStart"))
        try:
            await receiver.open()

            cold_start = ".1.3.6.1.6.3.1.1.5.1"
            sysname_0 = ".1.3.6.1.2.1.1.5.0"
            await send_trap_externally(cold_start, sysname_0, "s", "'MockDevice'")
            assert observer.called
        finally:
            receiver.close()

    @pytest.mark.skipif(not shutil.which("snmptrap"), reason="Cannot find snmptrap command line program")
    @pytest.mark.asyncio
    async def test_when_observer_raises_unhandled_exception_it_should_log_it(
        self, state_with_localhost, event_loop, caplog
    ):
        receiver = TrapReceiver(address="127.0.0.1", port=1162, loop=event_loop, state=state_with_localhost)
        receiver.add_community("public")
        crashing_observer = Mock()
        crashing_observer.side_effect = ValueError("mocked exception")
        receiver.observe(crashing_observer, ("SNMPv2-MIB", "coldStart"))
        try:
            await receiver.open()

            cold_start = ".1.3.6.1.6.3.1.1.5.1"
            sysname_0 = ".1.3.6.1.2.1.1.5.0"
            with caplog.at_level(logging.INFO):
                await send_trap_externally(cold_start, sysname_0, "s", "'MockDevice'")
                assert "ValueError" in caplog.text
                assert "mocked exception" in caplog.text
        finally:
            receiver.close()


@pytest.fixture
def state_with_localhost():
    localhost = ipaddress.ip_address("127.0.0.1")
    state = ZinoState()
    state.devices.devices["localhost"] = DeviceState(name="localhost", addresses={localhost})
    state.addresses[localhost] = "localhost"
    yield state


async def send_trap_externally(*args: str):
    args = " ".join(args)
    proc = await asyncio.create_subprocess_shell(f"snmptrap -v 2c -c public localhost:1162 '' {args}")
    await proc.communicate()
    assert proc.returncode == 0, "snmptrap command exited with error"
