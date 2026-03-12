"""Tests for the zping module."""

import asyncio
import subprocess
from unittest.mock import AsyncMock, patch

import pytest

from zino.zping import ZpingError, format_uptime, get_zino_uptime


class TestFormatUptime:
    """Tests for format_uptime."""

    def test_when_seconds_is_zero_then_it_should_return_zero_seconds(self):
        assert format_uptime(0) == "0 seconds"

    def test_when_seconds_is_one_then_it_should_use_singular_form(self):
        assert format_uptime(1) == "1 second"

    def test_when_seconds_is_greater_than_one_then_it_should_use_plural_form(self):
        assert format_uptime(42) == "42 seconds"

    def test_when_value_is_exactly_one_minute_then_it_should_return_one_minute(self):
        assert format_uptime(60) == "1 minute"

    def test_when_value_is_exactly_one_hour_then_it_should_return_one_hour(self):
        assert format_uptime(3600) == "1 hour"

    def test_when_value_is_exactly_one_day_then_it_should_return_one_day(self):
        assert format_uptime(86400) == "1 day"

    def test_when_all_components_are_nonzero_then_it_should_include_all(self):
        seconds = 1 * 86400 + 2 * 3600 + 3 * 60 + 4
        assert format_uptime(seconds) == "1 day, 2 hours, 3 minutes, 4 seconds"

    def test_when_minutes_is_zero_then_it_should_be_omitted(self):
        seconds = 5 * 86400 + 3 * 3600 + 7
        assert format_uptime(seconds) == "5 days, 3 hours, 7 seconds"

    def test_when_hours_and_seconds_are_zero_then_they_should_be_omitted(self):
        seconds = 2 * 86400 + 30 * 60
        assert format_uptime(seconds) == "2 days, 30 minutes"

    def test_when_days_is_greater_than_one_then_it_should_use_plural_form(self):
        assert format_uptime(2 * 86400) == "2 days"

    def test_when_uptime_is_large_then_it_should_format_all_components(self):
        seconds = 365 * 86400 + 23 * 3600 + 59 * 60 + 59
        assert format_uptime(seconds) == "365 days, 23 hours, 59 minutes, 59 seconds"

    def test_when_seconds_is_negative_then_it_should_raise_value_error(self):
        with pytest.raises(ValueError, match="negative"):
            format_uptime(-1)


@patch("zino.zping.SnmpEngine")
class TestGetZinoUptime:
    """Tests for get_zino_uptime with mocked SNMP."""

    @pytest.mark.asyncio
    async def test_when_agent_responds_then_it_should_return_uptime_as_int(self, _):
        mock_var_binds = [("1.3.6.1.4.1.2428.130.1.1.1.0", 42)]
        with patch("zino.zping.getCmd", new_callable=AsyncMock, return_value=(None, None, None, mock_var_binds)):
            result = await get_zino_uptime()
        assert result == 42

    @pytest.mark.asyncio
    async def test_when_error_indication_is_set_then_it_should_raise_zping_error(self, _):
        with patch("zino.zping.getCmd", new_callable=AsyncMock, return_value=("requestTimedOut", None, None, [])):
            with pytest.raises(ZpingError, match="requestTimedOut"):
                await get_zino_uptime()

    @pytest.mark.asyncio
    async def test_when_response_is_empty_then_it_should_raise_zping_error(self, _):
        with patch("zino.zping.getCmd", new_callable=AsyncMock, return_value=(None, None, None, [])):
            with pytest.raises(ZpingError, match="Empty response"):
                await get_zino_uptime()

    @pytest.mark.asyncio
    async def test_when_snmp_raises_exception_then_it_should_raise_zping_error(self, _):
        with patch("zino.zping.getCmd", new_callable=AsyncMock, side_effect=OSError("Connection refused")):
            with pytest.raises(ZpingError, match="SNMP request failed"):
                await get_zino_uptime()


@pytest.fixture
async def running_agent(unused_udp_port):
    """Start the SNMP agent as a subprocess and ensure it's ready."""
    process = subprocess.Popen(
        ["python", "-m", "zino.snmp.agent", "--port", str(unused_udp_port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    await asyncio.sleep(1)
    try:
        yield unused_udp_port
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


@pytest.mark.asyncio
async def test_when_agent_is_running_then_get_zino_uptime_should_return_valid_uptime(running_agent):
    """Integration test that get_zino_uptime works against a real agent."""
    port = running_agent
    uptime = await get_zino_uptime(host="127.0.0.1", port=port, timeout=5)
    assert isinstance(uptime, int)
    assert 0 <= uptime <= 10
