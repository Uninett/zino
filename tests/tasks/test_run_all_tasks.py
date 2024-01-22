import pytest

from zino.tasks import run_all_tasks, run_registered_tasks
from zino.tasks.errors import DeviceUnreachableError


class TestRunAllTasks:
    @pytest.mark.asyncio
    async def test_does_not_raise_error_if_device_is_unreachable(self, unreachable_task):
        assert (await run_all_tasks(unreachable_task.device, unreachable_task.state)) is None


class TestRunRegisteredTasks:
    @pytest.mark.asyncio
    async def test_raises_error_if_device_is_unreachable(self, unreachable_task):
        """The rest of the registered tasks are cancelled as a result of this"""
        with pytest.raises(DeviceUnreachableError):
            await run_registered_tasks(unreachable_task.device, unreachable_task.state)
