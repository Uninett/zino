"""Tests for zino.debug module."""

import logging
from unittest.mock import AsyncMock, Mock, patch

import pytest

from zino.config.models import PollDevice
from zino.debug import debug_log_timeout_error
from zino.state import ZinoState
from zino.tasks.task import Task


class DummyTask(Task):
    """Dummy task for testing."""

    async def run(self):
        """Run the task."""
        await self.do_snmp_operation()

    async def do_snmp_operation(self):
        """Simulate an SNMP operation that times out."""
        pass


class TestDebugLogTimeoutError:
    """Tests for debug_log_timeout_error function."""

    @pytest.fixture
    def dummy_device(self):
        """Create a dummy device."""
        return PollDevice(
            name="test-router",
            address="10.0.0.1",
            community="public",
        )

    @pytest.fixture
    def dummy_task(self, dummy_device):
        """Create a dummy task instance."""
        return DummyTask(dummy_device, ZinoState(), Mock())

    async def test_it_should_log_task_details(self, dummy_task, caplog):
        """Test that task frame information is logged correctly."""

        # Make the task's do_snmp_operation raise a TimeoutError
        async def raise_timeout():
            raise TimeoutError("Simulated timeout")

        dummy_task.do_snmp_operation = raise_timeout

        try:
            await dummy_task.run()
        except TimeoutError:
            with caplog.at_level(logging.DEBUG):
                debug_log_timeout_error("test-router", DummyTask)

        assert "test-router: TimeoutError in DummyTask" in caplog.text
        assert "test_debug.py" in caplog.text

    async def test_when_called_without_task_frame_in_stack_then_it_should_not_crash(self, caplog):
        """Test behavior when no task frame is found in stack."""
        try:
            raise TimeoutError("Direct timeout")
        except TimeoutError:
            with caplog.at_level(logging.DEBUG):
                debug_log_timeout_error("test-router", Mock)

        assert "TimeoutError in" not in caplog.text

    async def test_when_called_without_snmp_frame_in_stack_then_it_should_only_log_task_info(self, dummy_task, caplog):
        """Test behavior when no SNMP frame is found in stack."""

        # Create a timeout that happens in the task but not in SNMP
        async def non_snmp_timeout():
            raise TimeoutError("Non-SNMP timeout")

        dummy_task.do_snmp_operation = non_snmp_timeout

        try:
            await dummy_task.run()
        except TimeoutError:
            with caplog.at_level(logging.DEBUG):
                debug_log_timeout_error("test-router", DummyTask)

        assert "test-router: TimeoutError in DummyTask" in caplog.text
        assert "SNMP operation failed" not in caplog.text

    async def test_when_real_snmp_object_times_out_then_it_should_be_detected(self, dummy_device, caplog):
        """Test with a more realistic SNMP timeout scenario."""
        from zino.snmp import SNMP

        class RealSnmpTask(Task):
            async def run(self):
                result = await self.snmp.get("SNMPv2-MIB", "sysUpTime", 0)
                return result

        task = RealSnmpTask(dummy_device, ZinoState(), Mock())

        mock_snmp_obj = Mock(spec=SNMP)
        mock_snmp_obj.__class__.__name__ = "SNMP"

        with patch.object(task, "snmp", mock_snmp_obj):
            task.snmp.get = AsyncMock(side_effect=TimeoutError())

            try:
                await task.run()
            except TimeoutError:
                with caplog.at_level(logging.DEBUG):
                    debug_log_timeout_error("test-router", RealSnmpTask)

        assert "test-router: TimeoutError in RealSnmpTask" in caplog.text

    async def test_when_timeout_occurs_in_snmp_operation_then_both_task_and_snmp_details_should_be_logged(
        self, dummy_task, caplog
    ):
        """Test that both task frame and SNMP operation details are logged."""
        import collections
        from unittest.mock import MagicMock

        with patch("zino.debug.inspect.trace") as mock_trace:
            # Create mock frames for both task and SNMP
            task_frame = Mock()
            task_frame.f_locals = {"self": dummy_task}

            snmp_frame = Mock()
            snmp_obj = MagicMock()
            snmp_obj.__class__.__name__ = "SNMP"
            snmp_frame.f_locals = {"self": snmp_obj, "oid": ("IF-MIB", "ifName"), "max_repetitions": 10}

            # Create FrameInfo objects
            FrameInfo = collections.namedtuple(
                "FrameInfo", ["frame", "filename", "lineno", "function", "code_context", "index"]
            )
            task_frame_info = FrameInfo(task_frame, "tasks.py", 50, "run", ["await self.snmp.getbulk(...)"], 0)
            snmp_frame_info = FrameInfo(
                snmp_frame, "snmp.py", 100, "getbulk", ["return await self.session.agetbulk(...)"], 0
            )

            mock_trace.return_value = [snmp_frame_info, task_frame_info]

            with caplog.at_level(logging.DEBUG):
                debug_log_timeout_error("test-router", DummyTask)

        # Should log both task info and SNMP details
        assert "test-router: TimeoutError in DummyTask.run" in caplog.text
        assert "test-router: SNMP operation failed: operation=GET-BULK" in caplog.text
        assert "max_repetitions=10" in caplog.text


async def test_extract_snmp_operation_details_should_use_first_snmp_frame():
    """Test that _extract_snmp_operation_details returns first SNMP frame found."""
    from unittest.mock import MagicMock

    from zino.debug import _extract_snmp_operation_details

    # Create mock frames
    frame1 = MagicMock()
    frame1.frame.f_locals = {"self": MagicMock(__class__=type("NotSNMP", (), {})), "oid": "test1"}
    frame1.function = "some_function"

    frame2 = MagicMock()
    snmp_obj = MagicMock()
    snmp_obj.__class__.__name__ = "SNMP"
    frame2.frame.f_locals = {"self": snmp_obj, "oid": "test2", "max_repetitions": 10}
    frame2.function = "getbulk"

    frame3 = MagicMock()
    frame3.frame.f_locals = {"self": snmp_obj, "oid": "test3"}
    frame3.function = "get"

    frames = [frame1, frame2, frame3]

    result = _extract_snmp_operation_details(frames)

    # Should return details from frame2 (first SNMP frame)
    assert result == "operation=GET-BULK, oid=test2, max_repetitions=10"


@pytest.mark.parametrize(
    "function_name,locals_dict,expected_result",
    [
        ("get", {"oid": ("SNMPv2-MIB", "sysUpTime", 0)}, "operation=GET, oid=('SNMPv2-MIB', 'sysUpTime', 0)"),
        (
            "get2",
            {"variables": [("SNMPv2-MIB", "sysUpTime", 0)]},
            "operation=GET, variables=[('SNMPv2-MIB', 'sysUpTime', 0)]",
        ),
        ("getnext", {"oid": ("IF-MIB", "ifName", "1")}, "operation=GET-NEXT, oid=('IF-MIB', 'ifName', '1')"),
        ("getnext2", {"variables": [("IF-MIB", "ifName")]}, "operation=GET-NEXT, variables=[('IF-MIB', 'ifName')]"),
        ("walk", {"oid": ("IF-MIB", "ifName")}, "operation=WALK (via GET-NEXT), oid=('IF-MIB', 'ifName')"),
        (
            "getbulk",
            {"oid": ("IF-MIB", "ifName"), "max_repetitions": 10},
            "operation=GET-BULK, oid=('IF-MIB', 'ifName'), max_repetitions=10",
        ),
        (
            "getbulk2",
            {"variables": [("IF-MIB", "ifName")], "max_repetitions": 15},
            "operation=GET-BULK, variables=[('IF-MIB', 'ifName')], max_repetitions=15",
        ),
        (
            "bulkwalk",
            {"oid": ("IF-MIB", "ifName"), "max_repetitions": 20},
            "operation=GET-BULK, oid=('IF-MIB', 'ifName'), max_repetitions=20",
        ),
        (
            "sparsewalk",
            {"variables": [("IF-MIB", "ifName")], "max_repetitions": 25},
            "operation=GET-BULK, variables=[('IF-MIB', 'ifName')], max_repetitions=25",
        ),
        ("custom_op", {"oid": "some_oid"}, "operation=custom_op, oid=some_oid"),
    ],
)
async def test_format_snmp_operation_info_should_format_snmp_operation_data_correctly(
    function_name, locals_dict, expected_result
):
    """Test _format_snmp_operation_info function formats various operations correctly."""
    from zino.debug import _format_snmp_operation_info

    result = _format_snmp_operation_info(function_name, locals_dict)
    assert result == expected_result
