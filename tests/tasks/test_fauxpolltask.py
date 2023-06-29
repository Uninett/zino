from unittest.mock import Mock

import pytest

from zino.state import ZinoState
from zino.tasks.fauxpolltask import FauxPollTask


@pytest.mark.asyncio
async def test_fauxpolltask_runs_without_error():
    device = Mock(name="mock-sw")
    state = ZinoState()
    task = FauxPollTask(device, state)
    assert (await task.run()) is None
