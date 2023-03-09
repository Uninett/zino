import pytest


def test_zino_version_should_be_available():
    from zino import version

    assert version.__version__
    assert version.__version_tuple__


def test_when_polldevs_is_empty_zino_should_exit_quickly(empty_polldevs_conf):
    from zino.zino import init_async

    assert not init_async(empty_polldevs_conf)


@pytest.fixture
def empty_polldevs_conf(tmp_path):
    name = tmp_path.joinpath("polldevs.cf")
    with open(name, "w") as conf:
        conf.write("")
    yield name
