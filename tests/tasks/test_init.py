import logging
from ipaddress import IPv4Address
from unittest.mock import Mock, patch

from zino.config.models import PollDevice
from zino.state import ZinoState
from zino.tasks import get_registered_tasks, run_registered_tasks


class TimeoutTask:
    """Task that will raise TimeoutError when run."""

    def __init__(self, device, state, config):
        self.device = device
        self.state = state
        self.config = config

    async def run(self):
        raise TimeoutError("Simulated timeout in task")


def test_task_registry_should_be_populated_by_default():
    tasks = get_registered_tasks()
    assert len(tasks) > 0


async def test_when_task_raises_timeout_error_then_it_should_be_logged_with_debug_details(caplog):
    """Test that TimeoutError in run_registered_tasks triggers error logging and debug_log_timeout_error."""
    device = PollDevice(name="test-device", address=IPv4Address("10.0.0.1"), community="public")
    state = ZinoState()
    config = Mock()

    # Mock get_registered_tasks to return our test task
    with patch("zino.tasks.get_registered_tasks") as mock_get_tasks:
        mock_get_tasks.return_value = [TimeoutTask]

        # Mock debug_log_timeout_error to verify it's called
        with patch("zino.tasks.debug_log_timeout_error") as mock_debug_log:
            with caplog.at_level(logging.ERROR):
                await run_registered_tasks(device, state, config)

            # Verify error was logged with correct message
            assert "test-device: TimeoutTask raised an unexpected TimeoutError mid-run" in caplog.text
            assert "cancelling remaining tasks in this run" in caplog.text

            # Verify debug_log_timeout_error was called with correct arguments
            mock_debug_log.assert_called_once_with("test-device", TimeoutTask, logger=logging.getLogger("zino.tasks"))


async def test_when_task_raises_timeout_error_then_remaining_tasks_should_be_cancelled():
    """Test that TimeoutError in run_registered_tasks causes early return, cancelling remaining tasks."""
    device = PollDevice(name="test-device", address=IPv4Address("10.0.0.1"), community="public")
    state = ZinoState()
    config = Mock()

    # Track which tasks were run
    tasks_run = []

    class FirstTask:
        """First task that runs successfully."""

        def __init__(self, device, state, config):
            pass

        async def run(self):
            tasks_run.append("FirstTask")

    class TimeoutTaskTracked:
        """Task that will raise TimeoutError after recording it ran."""

        def __init__(self, *args, **kwargs):
            pass

        async def run(self):
            tasks_run.append("TimeoutTask")
            raise TimeoutError("Simulated timeout")

    class ThirdTask:
        """Task that should never run due to timeout."""

        def __init__(self, *args, **kwargs):
            pass

        async def run(self):
            tasks_run.append("ThirdTask")

    class FourthTask:
        """Another task that should never run."""

        def __init__(self, *args, **kwargs):
            pass

        async def run(self):
            tasks_run.append("FourthTask")

    # Mock get_registered_tasks to return our test tasks
    with patch("zino.tasks.get_registered_tasks") as mock_get_tasks:
        mock_get_tasks.return_value = [FirstTask, TimeoutTaskTracked, ThirdTask, FourthTask]

        # Mock debug_log_timeout_error to avoid side effects
        with patch("zino.tasks.debug_log_timeout_error"):
            await run_registered_tasks(device, state, config)

    # Verify only tasks before the timeout were run
    assert tasks_run == ["FirstTask", "TimeoutTask"]
    # ThirdTask and FourthTask should NOT be in the list
    assert "ThirdTask" not in tasks_run
    assert "FourthTask" not in tasks_run
