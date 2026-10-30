"""Tests for the various helper/development binaries and scripts in the zino package"""

import os
import signal
import subprocess
import time

import pytest


def test_zino_help_screen_runs_without_error():
    assert subprocess.check_call(["zino", "--help"]) == 0


def test_getuptime_help_runs_without_error(polldevs_conf, monkeypatch):
    monkeypatch.chdir(os.path.dirname(polldevs_conf))
    assert subprocess.check_call(["python", "-m", "zino.getuptime", "-h"]) == 0


def test_polltest_help_runs_without_error(polldevs_conf, monkeypatch):
    monkeypatch.chdir(os.path.dirname(polldevs_conf))
    assert subprocess.check_call(["python", "-m", "zino.polltest", "-h"]) == 0


@pytest.mark.parametrize("sig", [signal.SIGINT, signal.SIGTERM])
def test_when_stopped_by_signal_then_zino_should_exit_cleanly_and_dump_state(zino_conf, sig):
    process = subprocess.Popen(["zino", "--trap-port", "0"], cwd=zino_conf.parent)
    time.sleep(1)
    process.send_signal(sig)
    process.wait()

    assert process.returncode == 0, f"Process exited with code {process.returncode}"
    assert (zino_conf.parent / "zino-state.json").exists()


def test_when_run_from_empty_directory_it_should_log_error_and_exit(tmp_path_factory):
    cwd = tmp_path_factory.mktemp("empty")
    expected_error = b"No such file or directory: 'secrets'"
    result = subprocess.run(["zino", "--trap-port", "0"], cwd=cwd, capture_output=True)
    assert expected_error in result.stderr
