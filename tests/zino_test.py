def test_zino_version_should_be_available():
    from zino import version

    assert version.__version__
    assert version.__version_tuple__
