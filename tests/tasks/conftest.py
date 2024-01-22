from unittest.mock import patch

import pytest

from zino.config.models import PollDevice
from zino.state import ZinoState
from zino.tasks.reachabletask import ReachableTask


@pytest.fixture()
def reachable_task(snmpsim, snmp_test_port):
    device = PollDevice(name="buick.lab.example.org", address="127.0.0.1", port=snmp_test_port)
    state = ZinoState()
    task = ReachableTask(device, state)
    yield task
    task._deschedule_extra_job()


@pytest.fixture()
def unreachable_task():
    device = PollDevice(name="nonexist", address="127.0.0.1", community="invalid", port=666)
    state = ZinoState()
    task = ReachableTask(device, state)
    with patch("zino.tasks.task.SNMP.get") as get_mock:
        get_mock.side_effect = TimeoutError
        yield task
    task._deschedule_extra_job()
