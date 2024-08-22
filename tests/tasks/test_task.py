from unittest.mock import patch

import pytest

from zino.config.models import PollDevice
from zino.state import ZinoState
from zino.tasks.reachabletask import ReachableTask


class TestTask:

    async def test_get_sysuptime_returns_uptime(self, snmpsim, snmp_test_port):
        device = PollDevice(
            name="buick.lab.example.org",
            address="127.0.0.1",
            community="public",
            port=snmp_test_port,
        )
        state = ZinoState()
        task = ReachableTask(device, state)
        uptime = await task._get_uptime()
        assert uptime

    async def test_get_sysuptime_raises_timeout_error(self):
        device = PollDevice(name="nonexist", address="127.0.0.1", community="invalid", port=666)
        state = ZinoState()
        task = ReachableTask(device, state)
        with patch("zino.tasks.task.SNMP.get") as get_mock:
            get_mock.side_effect = TimeoutError
            with pytest.raises(TimeoutError):
                await task._get_uptime()
