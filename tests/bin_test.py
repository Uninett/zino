"""Tests for the various helper/development binaries and scripts in the zino package"""

import os
import signal
import subprocess
import time


def test_zino_help_screen_runs_without_error():
    assert subprocess.check_call(["zino", "--help"]) == 0


def test_getuptime_help_runs_without_error(polldevs_conf, monkeypatch):
    monkeypatch.chdir(os.path.dirname(polldevs_conf))
    assert subprocess.check_call(["python", "-m", "zino.getuptime", "-h"]) == 0


def test_polltest_help_runs_without_error(polldevs_conf, monkeypatch):
    monkeypatch.chdir(os.path.dirname(polldevs_conf))
    assert subprocess.check_call(["python", "-m", "zino.polltest", "-h"]) == 0


def test_when_interrupted_by_ctrl_c_zino_should_exit_cleanly(zino_conf):
    process = subprocess.Popen(["zino", "--trap-port", "0"], cwd=zino_conf.parent)
    time.sleep(1)
    process.send_signal(signal.SIGINT)
    process.wait()

    assert process.returncode == 0, f"Process exited with code {process.returncode}"
