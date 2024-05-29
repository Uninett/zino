from unittest.mock import Mock

from zino.trapobservers.ignored_traps import IgnoreTraps


class TestIgnoreTraps:
    def test_when_handle_trap_is_called_it_should_return_false(self):
        observer = IgnoreTraps(state=Mock())
        assert not observer.handle_trap(trap=Mock())
