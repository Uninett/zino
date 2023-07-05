from zino.oid import OID


class TestOIDIsPrefix:
    def test_return_true_if_prefix(self):
        oid = OID(".1.2.3.4.5")
        assert oid.is_a_prefix_of(".1.2.3.4.5.6")

    def test_return_false_if_not_prefix(self):
        oid = OID(".5.4.3.2.1")
        assert not oid.is_a_prefix_of(".1.2.3.4.5.6")

    def test_return_false_if_prefix_equal_to_oid(self):
        oid = OID(".5.4.3.2.1")
        assert not oid.is_a_prefix_of(".5.4.3.2.1")


class TestOIDStripPrefix:
    def test_valid_prefix_is_stripped(self):
        oid = ".1.2.3.4.5"
        prefix = ".1.2"
        stripped_oid = OID(oid).strip_prefix(prefix)
        assert str(stripped_oid) == ".3.4.5"

    def test_invalid_prefix_is_not_stripped(self):
        oid = ".1.2.3.4.5"
        prefix = ".5.4"
        stripped_oid = OID(oid).strip_prefix(prefix)
        assert str(stripped_oid) == oid
