"""Tests for the various helper/development binaries and scripts in the zino package"""

import os
import signal
import socket
import subprocess
import time
from typing import IO

import pytest

from zino.api.server import ZinoServer


def test_zino_help_screen_runs_without_error():
    assert subprocess.check_call(["zino", "--help"]) == 0


def test_getuptime_help_runs_without_error(polldevs_conf, monkeypatch):
    monkeypatch.chdir(os.path.dirname(polldevs_conf))
    assert subprocess.check_call(["python", "-m", "zino.getuptime", "-h"]) == 0


def test_polltest_help_runs_without_error(polldevs_conf, monkeypatch):
    monkeypatch.chdir(os.path.dirname(polldevs_conf))
    assert subprocess.check_call(["python", "-m", "zino.polltest", "-h"]) == 0


@pytest.mark.parametrize("sig", [signal.SIGINT, signal.SIGTERM], ids=lambda sig: sig.name)
def test_when_stopped_by_signal_then_zino_should_exit_cleanly_and_dump_state(zino_conf, start_zino, sig):
    process = start_zino()
    process.send_signal(sig)
    _, stderr = process.communicate(timeout=30)

    assert process.returncode == 0, stderr.decode()
    assert (zino_conf.parent / "zino-state.json").exists()


@pytest.mark.parametrize("sig", [signal.SIGINT, signal.SIGTERM], ids=lambda sig: sig.name)
def test_when_signalled_twice_then_zino_should_log_that_it_aborted_the_final_state_dump(zino_conf, start_zino, sig):
    # Opening a FIFO for writing blocks until a reader appears, which holds Zino in its final state dump
    os.mkfifo(zino_conf.parent / "zino-state.json.tmp")
    process = start_zino()
    process.send_signal(sig)
    _wait_for_log_line(process.stderr, b"performing final state dump")
    # A signal that lands just before a blocking system call is not acted on until the call returns
    time.sleep(0.5)
    process.send_signal(sig)
    _, stderr = process.communicate(timeout=30)

    assert process.returncode == -sig, stderr.decode()
    assert b"aborting final state dump" in stderr


def test_when_run_from_empty_directory_it_should_log_error_and_exit(tmp_path_factory):
    cwd = tmp_path_factory.mktemp("empty")
    expected_error = b"No such file or directory: 'secrets'"
    result = subprocess.run(["zino", "--trap-port", "0"], cwd=cwd, capture_output=True)
    assert expected_error in result.stderr


@pytest.fixture
def start_zino(zino_conf):
    """Returns a function that starts Zino in the background, killing every Zino it started on teardown.

    The function returns once Zino is ready to handle shutdown signals. Its log line proves that this Zino holds the
    API port. Its API greeting then proves that its event loop, and therefore its signal handlers, are running.
    """
    processes = []

    def start():
        process = subprocess.Popen(["zino", "--trap-port", "0"], cwd=zino_conf.parent, stderr=subprocess.PIPE)
        processes.append(process)
        _wait_for_log_line(process.stderr, b"Serving notifications on")
        _wait_for_api_greeting()
        return process

    yield start
    for process in processes:
        process.kill()
        process.communicate()


def _wait_for_log_line(stream: IO[bytes], needle: bytes) -> None:
    """Reads lines from a Zino process' log output until one contains `needle`"""
    lines = []
    for line in iter(stream.readline, b""):
        if needle in line:
            return
        lines.append(line)
    pytest.fail(f"Zino exited without logging {needle!r}:\n{b''.join(lines).decode()}")


def _wait_for_api_greeting() -> None:
    """Connects to Zino's API and waits for the greeting that Zino only sends from its running event loop"""
    with socket.create_connection(("127.0.0.1", ZinoServer.API_PORT), timeout=30) as api:
        assert api.recv(1024).startswith(b"200 ")
