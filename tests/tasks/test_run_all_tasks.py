from unittest.mock import patch
from weakref import WeakValueDictionary

import pytest

from zino.config.models import Configuration, PollDevice
from zino.snmp import get_snmp_session
from zino.state import ZinoState
from zino.tasks import run_all_tasks, run_registered_tasks
from zino.tasks.errors import DeviceUnreachableError
from zino.tasks.task import Task
from zino.tasks.vendor import VendorTask


class TestRunAllTasks:
    async def test_does_not_raise_error_if_device_is_unreachable(self, unreachable_task):
        assert (await run_all_tasks(unreachable_task.device, unreachable_task.state, unreachable_task.config)) is None

    async def test_when_one_task_raises_device_unreachable_it_should_not_run_further_tasks(
        self, raising_task, non_raising_task
    ):
        mock_device = PollDevice(name="mock_device", address="127.0.0.1")
        state = ZinoState()
        config = Configuration()
        with patch("zino.tasks.get_registered_tasks") as get_registered_tasks:
            get_registered_tasks.return_value = [raising_task, non_raising_task]
            await run_all_tasks(mock_device, state, config)
            assert raising_task.was_run
            assert not non_raising_task.was_run

    async def test_when_all_tasks_have_run_then_their_shared_snmp_session_should_be_closed(
        self, snmpsim, snmp_test_port, monkeypatch
    ):
        # Tests otherwise disable session re-use, but here all tasks must share the session, as in production
        monkeypatch.setattr("zino.snmp._snmp_sessions", WeakValueDictionary())
        device = PollDevice(name="localhost", address="127.0.0.1", port=snmp_test_port)
        state = ZinoState()
        session = get_snmp_session(device)

        with patch("zino.tasks.get_registered_tasks", return_value=[VendorTask]):
            await run_all_tasks(device, state, Configuration())

        assert state.devices[device.name].enterprise_id
        assert not session._is_open


class TestRunRegisteredTasks:
    async def test_raises_error_if_device_is_unreachable(self, unreachable_task):
        """The rest of the registered tasks are cancelled as a result of this"""
        with pytest.raises(DeviceUnreachableError):
            await run_registered_tasks(unreachable_task.device, unreachable_task.state, unreachable_task.config)


@pytest.fixture()
def raising_task():
    class RaisingTask(Task):
        was_run = False

        async def run(self):
            RaisingTask.was_run = True
            raise DeviceUnreachableError("just testing")

    return RaisingTask


@pytest.fixture()
def non_raising_task():
    class NonRaisingTask(Task):
        was_run = False

        async def run(self):
            NonRaisingTask.was_run = True
            return True

    return NonRaisingTask
