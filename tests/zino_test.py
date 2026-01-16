import getpass
import grp
import hashlib
import logging
import os
import pwd
import secrets
import subprocess
import time
from argparse import Namespace
from datetime import timedelta
from unittest.mock import Mock, patch

import pexpect
import pytest

from zino import zino
from zino.scheduler import get_scheduler
from zino.time import now


def test_zino_version_should_be_available():
    from zino import version

    assert version.__version__
    assert version.__version_tuple__


def test_zino_help_screen_should_not_crash():
    assert subprocess.check_call(["zino", "--help"]) == 0


def test_zino_should_not_crash_right_away(polldevs_conf_with_no_routers, unused_udp_port, zino_conf):
    """This tests that the main function runs Zino for at least 2 seconds"""
    seconds_to_run_for = 2
    subprocess.check_call(
        [
            "zino",
            "--stop-in",
            str(seconds_to_run_for),
            "--polldevs",
            str(polldevs_conf_with_no_routers),
            "--config-file",
            str(zino_conf),
            "--trap-port",
            str(unused_udp_port),
        ]
    )


def test_zino_should_run_with_pollfile_name_in_config_file(polldevs_conf_with_no_routers, unused_udp_port, zino_conf):
    """This tests that the main function runs Zino for at least 2 seconds when
    the name of the pollfile is defined in the config file
    """
    seconds_to_run_for = 2
    subprocess.check_call(
        [
            "zino",
            "--stop-in",
            str(seconds_to_run_for),
            "--config-file",
            str(zino_conf),
            "--trap-port",
            str(unused_udp_port),
        ]
    )


def test_zino_should_not_run_without_pollfile(zino_conf_with_non_existent_pollfile, unused_udp_port):
    """This tests that the main function does not Zino for at least 2 seconds when
    the name of the pollfile is defined in the config file, but does not exist
    """
    with pytest.raises(subprocess.CalledProcessError):
        seconds_to_run_for = 2
        subprocess.check_call(
            [
                "zino",
                "--stop-in",
                str(seconds_to_run_for),
                "--config-file",
                str(zino_conf_with_non_existent_pollfile),
                "--trap-port",
                str(unused_udp_port),
            ]
        )


def test_when_args_specified_config_file_does_not_exist_then_load_config_should_exit(tmp_path):
    args = Mock(config_file=tmp_path / "non_existent_file.toml")
    with pytest.raises(SystemExit):
        zino.load_config(args)


def test_when_no_config_file_specified_then_load_config_should_return_default_config(tmp_path):
    args = Mock(config_file=tmp_path / "non_existent_file.toml")
    config = zino.load_config(args)
    assert config, "load_config did not return default config for missing config file"


def test_when_logging_config_is_invalid_then_apply_logging_config_should_exit():
    with pytest.raises(SystemExit):
        zino.apply_logging_config({"loggers": {"zino": {"level": "invalid"}}})


def test_zino_should_not_run_with_invalid_conf_file(invalid_zino_conf, unused_udp_port):
    """This tests that the main function does not Zino for at least 2 seconds when
    the name of the pollfile is defined in the config file, but does not exist
    """
    with pytest.raises(subprocess.CalledProcessError):
        seconds_to_run_for = 2
        subprocess.check_call(
            [
                "zino",
                "--stop-in",
                str(seconds_to_run_for),
                "--config-file",
                str(invalid_zino_conf),
                "--trap-port",
                str(unused_udp_port),
            ]
        )


def test_zino_argparser_works(polldevs_conf):
    parser = zino.parse_args(["--polldevs", str(polldevs_conf)])
    assert isinstance(parser, Namespace)


@pytest.mark.skipif(os.geteuid() == 0, reason="cannot test while being root")
def test_when_unprivileged_user_asks_for_privileged_port_zino_should_exit_with_error(polldevs_conf_with_no_routers):
    seconds_to_run_for = 5
    with pytest.raises(subprocess.CalledProcessError):
        subprocess.check_call(
            [
                "zino",
                "--stop-in",
                str(seconds_to_run_for),
                "--polldevs",
                str(polldevs_conf_with_no_routers),
                "--trap-port",
                "162",
            ]
        )


@patch("zino.zino.switch_to_user")
async def test_when_args_specify_user_zino_init_event_loop_should_attempt_to_switch_users(switch_to_user, event_loop):
    """Detect attempt to user switching by patching in a mock exception.  This is to avoid setting up the full Zino
    daemon and mucking up the event loop and state, by ensuring we exit as soon as switch_to_user is called.
    """

    class MockError(Exception):
        pass

    zino.switch_to_user.side_effect = MockError()
    with pytest.raises(MockError):
        try:
            zino.init_event_loop(args=Mock(trap_port=0, user="nobody"), loop=event_loop)
        except MockError:
            raise
        except Exception:
            pass


class TestZinoRescheduleDumpStateOnCommit:
    def test_when_more_than_10_seconds_remains_until_next_dump_it_should_reschedule(self):
        scheduler = get_scheduler()
        mock_job = Mock(next_run_time=now() + timedelta(minutes=5))
        mock_event = Mock(id=42)

        with patch.object(scheduler, "get_job") as get_job:
            get_job.return_value = mock_job
            zino.reschedule_dump_state_on_commit(mock_event)
            assert mock_job.modify.called

    def test_when_less_than_10_seconds_remains_until_next_dump_it_should_not_reschedule(self):
        scheduler = get_scheduler()
        mock_job = Mock(next_run_time=now() + timedelta(seconds=5))
        mock_event = Mock(id=42)

        with patch.object(scheduler, "get_job") as get_job:
            get_job.return_value = mock_job
            zino.reschedule_dump_state_on_commit(mock_event)
            assert not mock_job.modify.called


class TestZinoRescheduleDumpStateOnPmChange:
    def test_when_more_than_10_seconds_remain_until_next_dump_it_should_reschedule(self):
        scheduler = get_scheduler()
        mock_job = Mock(next_run_time=now() + timedelta(minutes=5))

        with patch.object(scheduler, "get_job") as get_job:
            get_job.return_value = mock_job
            zino.reschedule_dump_state_on_pm_change()
            assert mock_job.modify.called

    def test_when_less_than_10_seconds_remain_until_next_dump_it_should_not_reschedule(self):
        scheduler = get_scheduler()
        mock_job = Mock(next_run_time=now() + timedelta(seconds=5))

        with patch.object(scheduler, "get_job") as get_job:
            get_job.return_value = mock_job
            zino.reschedule_dump_state_on_pm_change()
            assert not mock_job.modify.called


class TestSwitchUser:
    def test_when_switching_to_current_user_it_should_succeed(self):
        username = getpass.getuser()
        assert zino.switch_to_user(username)

    def test_when_user_does_not_exist_it_should_return_false(self):
        random_username = secrets.token_hex(5)
        print(f"attempting switch to user {random_username!r}")
        assert not zino.switch_to_user(random_username)

    @patch("pwd.getpwnam")
    @patch("grp.getgrall")
    @patch("os.setgid")
    @patch("os.setgroups")
    @patch("os.setuid")
    def test_when_user_exists_it_should_switch_correctly_to_uid_gid_and_groups(
        self, getpwnam, getgrall, setgid, setgroups, setuid
    ):
        random_username = secrets.token_hex(5)
        pwd.getpwnam.return_value = Mock(pw_uid=666, pw_gid=999)
        grp.getgrall.return_value = [Mock(gr_gid=4242, gr_mem=[random_username])]

        assert zino.switch_to_user(random_username)
        os.setgid.assert_called_once_with(999)
        os.setuid.assert_called_once_with(666)
        os.setgroups.assert_called_once_with([4242])

    @patch("pwd.getpwnam")
    @patch("grp.getgrall")
    @patch("os.setgid")
    @patch("os.setgroups")
    @patch("os.setuid")
    def test_when_setgid_raises_oserror_it_should_return_false(self, getpwnam, getgrall, setgid, setgroups, setuid):
        random_username = secrets.token_hex(5)
        pwd.getpwnam.return_value = Mock(pw_uid=666, pw_gid=999)
        grp.getgrall.return_value = [Mock(gr_gid=4242, gr_mem=[random_username])]
        os.setgid.side_effect = OSError("Mock error")

        assert not zino.switch_to_user(random_username)


class TestCountReachableObjects:
    def test_it_should_count_queried_classes(self):
        counts = zino._count_reachable_objects(str, int)
        assert int in counts
        assert counts[int] > 0
        assert str in counts
        assert counts[str] > 0

    def test_it_should_not_count_non_queried_classes(self):
        counts = zino._count_reachable_objects(str)
        assert int not in counts


class TestLogSnmpSessionState:
    def test_when_netsnmpy_is_backend_it_should_log_low_level_details(self, state_with_localhost, caplog):
        import zino.snmp.netsnmpy_backend as backend

        with patch.object(zino.state, attribute="state", new=state_with_localhost):
            with patch.object(zino, attribute="import_snmp_backend") as import_snmp_backend:
                import_snmp_backend.return_value = backend
                with caplog.at_level(logging.DEBUG):
                    zino.log_snmp_session_stats()
                    assert "gc reachable (low-level)=" in caplog.text

    def test_when_pysnmp_is_backend_it_should_not_log_low_level_details(self, state_with_localhost, caplog):
        import zino.snmp.pysnmp_backend as backend

        with patch.object(zino.state, attribute="state", new=state_with_localhost):
            with patch.object(zino, attribute="import_snmp_backend") as import_snmp_backend:
                import_snmp_backend.return_value = backend
                with caplog.at_level(logging.DEBUG):
                    zino.log_snmp_session_stats()
                    assert "gc reachable (low-level)=" not in caplog.text

    def test_when_debug_logging_is_not_enabled_it_should_not_log_anything(self, state_with_localhost, caplog):
        import zino.snmp.netsnmpy_backend as backend

        with patch.object(zino.state, attribute="state", new=state_with_localhost):
            with patch.object(zino, attribute="import_snmp_backend") as import_snmp_backend:
                import_snmp_backend.return_value = backend
                with caplog.at_level(logging.INFO):
                    zino.log_snmp_session_stats()
                    assert "gc reachable" not in caplog.text


class TestSecretsFileConfiguration:
    def test_users_from_secrets_file_should_be_able_to_authenticate(
        self, polldevs_conf_with_no_routers, zino_conf, secrets_file
    ):
        """Test connecting to the server, handling SHA1 challenge, and asserting successful login."""
        # Start the process
        zino_process = subprocess.Popen(["zino", "--config-file", str(zino_conf), "--trap-port", "0"])
        with open(secrets_file, "r") as f:
            username, password = f.readline().strip().split(" ", 1)
        time.sleep(1)  # Wait for the server to start
        try:
            client = pexpect.spawn("telnet localhost 8001", timeout=5)
            client.expect("200 ([a-f0-9]+) Hello, there")
            challenge = client.match.group(1).decode("utf-8")

            response = hashlib.sha1((challenge + " " + password).encode("utf-8")).hexdigest()

            client.sendline(f"USER {username} {response}")
            client.expect(["200 ok", "500 Authentication failure"])
            assert "200 ok" in client.after.decode("utf-8")

        finally:
            zino_process.terminate()
