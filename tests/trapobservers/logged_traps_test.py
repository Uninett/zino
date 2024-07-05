import logging
from unittest.mock import Mock

import pytest

from zino.trapd import TrapMessage
from zino.trapobservers.logged_traps import RestartTrapLogger


class TestRestartTrapLogger:
    @pytest.mark.parametrize("trap_name", ["coldStart", "warmStart"])
    def test_when_handle_trap_is_called_it_should_log_trap_name(self, caplog, localhost_trap_originator, trap_name):
        observer = RestartTrapLogger(state=Mock())
        trap = TrapMessage(agent=localhost_trap_originator, mib="SNMPv2-MIB", name=trap_name)
        with caplog.at_level(logging.INFO):
            observer.handle_trap(trap=trap)
            assert f"localhost: {trap_name}" in caplog.text
