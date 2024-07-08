from unittest.mock import Mock

import pytest

from zino.trapobservers.ignored_traps import IgnoreTraps


class TestIgnoreTraps:
    @pytest.mark.asyncio
    async def test_when_handle_trap_is_called_it_should_return_false(self):
        observer = IgnoreTraps(state=Mock())
        assert not await observer.handle_trap(trap=Mock())
