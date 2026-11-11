"""Common fixtures for task tests.

Many task tests run tasks directly, without the `with` block that `run_all_tasks()` provides. Their SNMP sessions are
therefore only closed once garbage collected, which logs a "garbage collected while still open" warning. In these tests,
that warning is expected and harmless.
"""

from unittest.mock import patch

import pytest

from zino.config.models import Configuration, PollDevice
from zino.state import ZinoState
from zino.tasks.reachabletask import ReachableTask


@pytest.fixture()
def reachable_task(snmpsim, snmp_test_port):
    device = PollDevice(name="buick.lab.example.org", address="127.0.0.1", port=snmp_test_port)
    state = ZinoState()
    config = Configuration()
    state.devices.get(device.name)
    task = ReachableTask(device, state, config)
    yield task
    task._deschedule_extra_job()


@pytest.fixture()
def unreachable_task():
    device = PollDevice(name="nonexist", address="127.0.0.1", community="invalid", port=666)
    state = ZinoState()
    config = Configuration()
    state.devices.get(device.name)
    task = ReachableTask(device, state, config)
    with patch("zino.snmp.SNMP.get") as get_mock:
        get_mock.side_effect = TimeoutError
        yield task
    task._deschedule_extra_job()
