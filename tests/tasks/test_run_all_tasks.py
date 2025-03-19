from unittest.mock import patch

import pytest

from zino.config.models import PollDevice
from zino.state import ZinoState
from zino.tasks import run_all_tasks, run_registered_tasks
from zino.tasks.errors import DeviceUnreachableError
from zino.tasks.task import Task


class TestRunAllTasks:
    async def test_does_not_raise_error_if_device_is_unreachable(self, unreachable_task):
        assert (await run_all_tasks(unreachable_task.device, unreachable_task.state)) is None

    async def test_when_one_task_raises_device_unreachable_it_should_not_run_further_tasks(
        self, raising_task, non_raising_task
    ):
        mock_device = PollDevice(name="mock_device", address="127.0.0.1")
        state = ZinoState()
        with patch("zino.tasks.get_registered_tasks") as get_registered_tasks:
            get_registered_tasks.return_value = [raising_task, non_raising_task]
            await run_all_tasks(mock_device, state)
            assert raising_task.was_run
            assert not non_raising_task.was_run


class TestRunRegisteredTasks:
    async def test_raises_error_if_device_is_unreachable(self, unreachable_task):
        """The rest of the registered tasks are cancelled as a result of this"""
        with pytest.raises(DeviceUnreachableError):
            await run_registered_tasks(unreachable_task.device, unreachable_task.state)


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
