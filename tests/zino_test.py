import subprocess
from argparse import Namespace

from zino import zino


def test_zino_version_should_be_available():
    from zino import version

    assert version.__version__
    assert version.__version_tuple__


def test_zino_help_screen_should_not_crash():
    assert subprocess.check_call(["zino", "--help"]) == 0


def test_zino_argparser_works(polldevs_conf):
    parser = zino.parse_args(["--polldevs", str(polldevs_conf)])
    assert isinstance(parser, Namespace)
