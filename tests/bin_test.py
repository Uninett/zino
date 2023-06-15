"""Tests for the various helper/development binaries and scripts in the zino package"""
import os
import subprocess


def test_zino_help_screen_runs_without_error():
    assert subprocess.check_call(["zino", "--help"]) == 0


def test_getuptime_help_runs_without_error(polldevs_conf, monkeypatch):
    monkeypatch.chdir(os.path.dirname(polldevs_conf))
    assert subprocess.check_call(["python", "-m", "zino.getuptime", "-h"]) == 0


def test_polltest_help_runs_without_error(polldevs_conf, monkeypatch):
    monkeypatch.chdir(os.path.dirname(polldevs_conf))
    assert subprocess.check_call(["python", "-m", "zino.polltest", "-h"]) == 0
