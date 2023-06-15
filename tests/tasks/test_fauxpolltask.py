from unittest.mock import Mock

import pytest

from zino.tasks.fauxpolltask import FauxPollTask


@pytest.mark.asyncio
async def test_fauxpolltask_runs_without_error():
    device = Mock(name="mock-sw")
    task = FauxPollTask(device)
    assert (await task.run()) is None
