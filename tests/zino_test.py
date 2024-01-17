import subprocess
from argparse import Namespace
from datetime import timedelta
from unittest.mock import Mock, patch

from zino import zino
from zino.scheduler import get_scheduler
from zino.time import now


def test_zino_version_should_be_available():
    from zino import version

    assert version.__version__
    assert version.__version_tuple__


def test_zino_help_screen_should_not_crash():
    assert subprocess.check_call(["zino", "--help"]) == 0


def test_zino_should_not_crash_right_away(polldevs_conf_with_no_routers):
    """This tests that the main function runs Zino for at least 2 seconds"""
    seconds_to_run_for = 2
    subprocess.check_call(
        ["zino", "--stop-in", str(seconds_to_run_for), "--polldevs", str(polldevs_conf_with_no_routers)]
    )


def test_zino_argparser_works(polldevs_conf):
    parser = zino.parse_args(["--polldevs", str(polldevs_conf)])
    assert isinstance(parser, Namespace)


class TestZinoRescheduleDumpStateOnCommit:
    def test_when_more_than_10_seconds_remains_until_next_dump_it_should_reschedule(self):
        scheduler = get_scheduler()
        mock_job = Mock(next_run_time=now() + timedelta(minutes=5))

        with patch.object(scheduler, "get_job") as get_job:
            get_job.return_value = mock_job
            zino.reschedule_dump_state_on_commit(42)
            assert mock_job.modify.called

    def test_when_less_than_10_seconds_remains_until_next_dump_it_should_not_reschedule(self):
        scheduler = get_scheduler()
        mock_job = Mock(next_run_time=now() + timedelta(seconds=5))

        with patch.object(scheduler, "get_job") as get_job:
            get_job.return_value = mock_job
            zino.reschedule_dump_state_on_commit(42)
            assert not mock_job.modify.called
