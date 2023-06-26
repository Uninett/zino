from zino.oid import OID


class TestOIDPrefix:
    def test_return_true_if_prefix(self):
        oid = OID("1.2.3.4.5")
        assert oid.is_a_prefix_of("1.2.3.4.5.6")

    def test_return_false_if_not_prefix(self):
        oid = OID("5.4.3.2.1")
        assert not oid.is_a_prefix_of("1.2.3.4.5.6")

    def test_return_false_if_prefix_equal_to_oid(self):
        oid = OID("5.4.3.2.1")
        assert not oid.is_a_prefix_of("5.4.3.2.1")
