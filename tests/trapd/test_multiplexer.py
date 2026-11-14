"""Tests for on-demand starting of straps/nmtrapd trap multiplexers."""

import logging
import sys

import pytest

from zino.config.models import TrapConfiguration
from zino.trapd.multiplexer import MultiplexerLauncher, can_serve_configured_endpoint, is_local_host


class TestMultiplexerLauncher:
    def test_when_multiplexer_command_is_omitted_then_command_should_be_named_after_source(self):
        launcher = MultiplexerLauncher(TrapConfiguration(source="nmtrapd"))
        assert launcher.command == ["nmtrapd"]

    def test_when_multiplexer_command_is_set_then_command_should_be_used_verbatim(self):
        config = TrapConfiguration(source="straps", multiplexer_command=["/usr/pkg/bin/straps", "162"])
        launcher = MultiplexerLauncher(config)
        assert launcher.command == ["/usr/pkg/bin/straps", "162"]

    async def test_given_start_multiplexer_is_false_when_starting_then_it_should_not_start_anything(self):
        config = TrapConfiguration(source="straps", start_multiplexer=False, multiplexer_command=python("pass"))
        launcher = MultiplexerLauncher(config)
        assert await launcher.start() is False
        assert launcher._process is None

    async def test_when_command_can_be_spawned_then_start_should_return_true(self):
        launcher = MultiplexerLauncher(TrapConfiguration(source="straps", multiplexer_command=python("pass")))
        assert await launcher.start() is True
        await launcher._monitor_task

    async def test_when_command_does_not_exist_then_start_should_return_false(self, tmp_path):
        config = TrapConfiguration(source="straps", multiplexer_command=[str(tmp_path / "no-straps-here")])
        launcher = MultiplexerLauncher(config)
        assert await launcher.start() is False

    async def test_when_command_does_not_exist_then_it_should_log_an_error_with_a_config_hint(self, tmp_path, caplog):
        config = TrapConfiguration(source="straps", multiplexer_command=[str(tmp_path / "no-straps-here")])
        launcher = MultiplexerLauncher(config)
        with caplog.at_level(logging.ERROR):
            await launcher.start()
        assert "multiplexer_command" in caplog.text

    async def test_when_command_writes_to_stderr_then_it_should_be_logged_as_warning(self, caplog):
        command = python("import sys; print('unable to bind trap socket', file=sys.stderr)")
        launcher = MultiplexerLauncher(TrapConfiguration(source="straps", multiplexer_command=command))
        with caplog.at_level(logging.WARNING):
            await launcher.start()
            await launcher._monitor_task
        assert "straps: unable to bind trap socket" in caplog.text

    async def test_when_command_exits_with_error_then_exit_status_should_be_logged(self, caplog):
        command = python("raise SystemExit(3)")
        launcher = MultiplexerLauncher(TrapConfiguration(source="straps", multiplexer_command=command))
        with caplog.at_level(logging.WARNING):
            await launcher.start()
            await launcher._monitor_task
        assert "exited with status 3" in caplog.text

    @pytest.mark.timeout(5)
    async def test_given_started_process_is_still_running_when_starting_again_then_it_should_not_start_another(
        self,
    ):
        command = python("import time; time.sleep(30)")
        launcher = MultiplexerLauncher(TrapConfiguration(source="straps", multiplexer_command=command))
        await launcher.start()
        try:
            assert await launcher.start() is False
        finally:
            launcher._process.kill()
            await launcher._monitor_task

    async def test_given_started_process_has_exited_when_starting_again_then_it_should_start_another(self):
        launcher = MultiplexerLauncher(TrapConfiguration(source="straps", multiplexer_command=python("pass")))
        await launcher.start()
        await launcher._monitor_task
        assert await launcher.start() is True
        await launcher._monitor_task

    async def test_given_remote_nmtrapd_host_when_starting_then_it_should_not_start_anything(self):
        config = TrapConfiguration(
            source="nmtrapd", nmtrapd_host="trap.example.org", multiplexer_command=python("pass")
        )
        launcher = MultiplexerLauncher(config)
        assert await launcher.start() is False
        assert launcher._process is None

    def test_when_logging_unreachable_nmtrapd_then_it_should_point_at_syslog(self, caplog):
        launcher = MultiplexerLauncher(TrapConfiguration(source="nmtrapd"))
        launcher.log_unreachable(ConnectionRefusedError("Connection refused"))
        assert "syslog" in caplog.text

    def test_when_logging_unreachable_straps_then_it_should_name_the_command(self, caplog):
        launcher = MultiplexerLauncher(TrapConfiguration(source="straps"))
        launcher.log_unreachable(FileNotFoundError("No such file or directory"))
        assert "Started straps" in caplog.text
        assert "syslog" not in caplog.text


class TestCanServeConfiguredEndpoint:
    def test_given_default_straps_socket_then_it_should_return_true_without_warning(self, caplog):
        assert can_serve_configured_endpoint(TrapConfiguration(source="straps")) is True
        assert not caplog.records

    def test_given_non_stock_straps_socket_then_it_should_warn(self, caplog):
        config = TrapConfiguration(source="straps", straps_socket="/var/run/straps.sock")
        with caplog.at_level(logging.WARNING):
            assert can_serve_configured_endpoint(config) is True
        assert "/var/run/straps.sock" in caplog.text

    def test_given_default_nmtrapd_endpoint_then_it_should_return_true_without_warning(self, caplog):
        assert can_serve_configured_endpoint(TrapConfiguration(source="nmtrapd")) is True
        assert not caplog.records

    def test_given_remote_nmtrapd_host_then_it_should_return_false(self):
        config = TrapConfiguration(source="nmtrapd", nmtrapd_host="trap.example.org")
        assert can_serve_configured_endpoint(config) is False

    def test_given_remote_nmtrapd_host_then_it_should_warn_how_to_silence_the_warning(self, caplog):
        config = TrapConfiguration(source="nmtrapd", nmtrapd_host="trap.example.org")
        with caplog.at_level(logging.WARNING):
            can_serve_configured_endpoint(config)
        assert "start_multiplexer = false" in caplog.text
        assert "multiplexer_command" not in caplog.text

    def test_given_non_stock_nmtrapd_port_then_it_should_warn(self, caplog):
        config = TrapConfiguration(source="nmtrapd", nmtrapd_port=1703)
        with caplog.at_level(logging.WARNING):
            assert can_serve_configured_endpoint(config) is True
        assert "1703" in caplog.text


class TestIsLocalHost:
    @pytest.mark.parametrize("host", ["localhost", "127.0.0.1", "127.1.2.3", "::1"])
    def test_when_host_is_loopback_then_it_should_return_true(self, host):
        assert is_local_host(host) is True

    @pytest.mark.parametrize("host", ["trap.example.org", "192.0.2.1", "2001:db8::1"])
    def test_when_host_is_not_loopback_then_it_should_return_false(self, host):
        assert is_local_host(host) is False


def python(code: str) -> list[str]:
    """Returns a command line that runs code in a fresh Python interpreter, to stand in for a multiplexer."""
    return [sys.executable, "-c", code]
