import logging
from unittest.mock import Mock

import pytest

from zino.trapd import TrapMessage
from zino.trapobservers.logged_traps import (
    CiscoConfigManEventLogger,
    CiscoReloadTrapLogger,
    RestartTrapLogger,
)


class TestRestartTrapLogger:
    @pytest.mark.parametrize("trap_name", ["coldStart", "warmStart"])
    @pytest.mark.asyncio
    async def test_when_handle_trap_is_called_it_should_log_trap_name(
        self, caplog, localhost_trap_originator, trap_name
    ):
        observer = RestartTrapLogger(state=Mock())
        trap = TrapMessage(agent=localhost_trap_originator, mib="SNMPv2-MIB", name=trap_name)
        with caplog.at_level(logging.INFO):
            await observer.handle_trap(trap=trap)
            assert f"localhost: {trap_name}" in caplog.text


class TestCiscoReloadTrapLogger:
    @pytest.mark.asyncio
    async def test_when_handle_trap_is_called_it_should_log_reload(
        self,
        caplog,
        localhost_trap_originator,
    ):
        observer = CiscoReloadTrapLogger(state=Mock())
        trap = TrapMessage(agent=localhost_trap_originator, mib="CISCOTRAP-MIB", name="reload")
        with caplog.at_level(logging.INFO):
            await observer.handle_trap(trap=trap)
            assert "localhost: reload requested" in caplog.text


class TestCiscoConfigManEventLogger:
    @pytest.mark.asyncio
    async def test_when_handle_trap_is_called_it_should_log_config_change(
        self,
        caplog,
        localhost_trap_originator,
    ):
        observer = CiscoConfigManEventLogger(state=Mock())
        trap = TrapMessage(
            agent=localhost_trap_originator,
            mib="CISCO-CONFIG-MAN",
            name="ciscoConfigManEvent",
            variables=[
                Mock(var="ccmHistoryEventCommandSource", value="snmp"),
                Mock(var="ccmHistoryEventConfigSource", value="networkTftp"),
                Mock(var="ccmHistoryEventConfigDestination", value="startup"),
            ],
        )
        with caplog.at_level(logging.INFO):
            await observer.handle_trap(trap=trap)
            assert "localhost: config-change: cmd-src snmp conf-src networkTftp dst startup" in caplog.text
