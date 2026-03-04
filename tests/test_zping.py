"""Tests for the zping module."""

import asyncio
import subprocess
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from zino.zping import (
    SECONDS_PER_DAY,
    SECONDS_PER_HOUR,
    SECONDS_PER_MINUTE,
    ZpingError,
    format_uptime,
    get_zino_uptime,
    main,
)


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (0, "0 seconds"),
        (1, "1 second"),
        (
            1 * SECONDS_PER_DAY + 2 * SECONDS_PER_HOUR + 3 * SECONDS_PER_MINUTE + 4,
            "1 day, 2 hours, 3 minutes, 4 seconds",
        ),
        (5 * SECONDS_PER_DAY + 3 * SECONDS_PER_HOUR + 7, "5 days, 3 hours, 7 seconds"),
        (2 * SECONDS_PER_DAY + 30 * SECONDS_PER_MINUTE, "2 days, 30 minutes"),
    ],
)
def test_when_format_uptime_is_called_then_it_should_render_human_readable_string(seconds, expected):
    assert format_uptime(seconds) == expected


def test_when_seconds_is_negative_then_format_uptime_should_raise_value_error():
    with pytest.raises(ValueError, match="negative"):
        format_uptime(-1)


class TestGetZinoUptimeAgainstRealAgent:
    """End-to-end tests that exercise the SNMP protocol against a real Zino agent subprocess."""

    @pytest.mark.asyncio
    async def test_when_agent_is_running_then_it_should_return_uptime_as_int(self, running_agent):
        uptime = await get_zino_uptime(host="127.0.0.1", port=running_agent, timeout=2)
        assert isinstance(uptime, int)
        assert uptime >= 0

    @pytest.mark.asyncio
    async def test_when_no_agent_listens_then_it_should_raise_zping_error(self, unused_udp_port):
        with pytest.raises(ZpingError):
            await get_zino_uptime(host="127.0.0.1", port=unused_udp_port, timeout=1)


class TestGetZinoUptimeProtocolCorners:
    """Mocked tests for SNMP response shapes that a real Zino agent will not produce.

    These cover defensive branches in ``get_zino_uptime`` (SNMP error PDUs, empty
    var-bind lists). They cannot reasonably be triggered against a real agent, so
    the SNMP layer is mocked here — the assertions are about how ``get_zino_uptime``
    *interprets* such responses, not about the protocol exchange itself.
    """

    @pytest.mark.asyncio
    @patch("zino.zping.SnmpEngine")
    async def test_when_response_is_empty_then_it_should_raise_zping_error(self, _engine):
        with patch("zino.zping.getCmd", new_callable=AsyncMock, return_value=(None, None, None, [])):
            with pytest.raises(ZpingError, match="Empty response"):
                await get_zino_uptime()

    @pytest.mark.asyncio
    @patch("zino.zping.SnmpEngine")
    async def test_when_error_status_is_set_then_it_should_raise_zping_error(self, _engine):
        error_status = MagicMock()
        error_status.__bool__.return_value = True
        error_status.prettyPrint.return_value = "noSuchName"
        var_binds = [(MagicMock(__str__=lambda self: "1.3.6.1.4.1.2428.130.1.1.1.0"), None)]
        with patch(
            "zino.zping.getCmd",
            new_callable=AsyncMock,
            return_value=(None, error_status, 1, var_binds),
        ):
            with pytest.raises(ZpingError, match="noSuchName"):
                await get_zino_uptime()

    @pytest.mark.asyncio
    @patch("zino.zping.SnmpEngine")
    async def test_when_snmp_raises_exception_then_it_should_wrap_as_zping_error(self, _engine):
        with patch("zino.zping.getCmd", new_callable=AsyncMock, side_effect=OSError("synthetic")):
            with pytest.raises(ZpingError, match="SNMP request failed"):
                await get_zino_uptime()

    @pytest.mark.asyncio
    @patch("zino.zping.SnmpEngine")
    async def test_when_error_status_has_no_index_then_it_should_use_placeholder(self, _engine):
        error_status = MagicMock()
        error_status.__bool__.return_value = True
        error_status.prettyPrint.return_value = "genErr"
        with patch(
            "zino.zping.getCmd",
            new_callable=AsyncMock,
            return_value=(None, error_status, 0, []),
        ):
            with pytest.raises(ZpingError, match=r"genErr at \?"):
                await get_zino_uptime()


class TestMain:
    """Tests for the CLI entry point.

    ``asyncio.run`` is patched so these tests don't create and tear down an event loop
    — that would clear the current-loop pointer that ``pytest-asyncio<0.22`` relies on,
    breaking unrelated async tests later in the suite. The unit under test here is the
    argparse + stdout + exit-code wiring, not the loop.
    """

    def test_when_main_succeeds_then_it_should_print_uptime(self, capsys, monkeypatch):
        monkeypatch.setattr("sys.argv", ["zping"])
        with patch("zino.zping.asyncio.run", return_value=42):
            main()
        captured = capsys.readouterr()
        assert "Zino is alive" in captured.out
        assert "42 seconds" in captured.out

    def test_when_main_fails_then_it_should_exit_with_error(self, capsys, monkeypatch):
        monkeypatch.setattr("sys.argv", ["zping"])
        with patch("zino.zping.asyncio.run", side_effect=ZpingError("boom")):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "not reachable" in captured.err
        assert "boom" in captured.err


@pytest.fixture
async def running_agent(unused_udp_port):
    """Start the Zino SNMP agent as a subprocess and give it a moment to come up."""
    process = subprocess.Popen(
        [sys.executable, "-m", "zino.snmp.agent", "--port", str(unused_udp_port)],
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
