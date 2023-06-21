import pytest

from zino.config.models import PollDevice
from zino.snmp import SNMP


class TestSNMPRequests:
    def get_client(self, port):
        device = PollDevice(name="buick.lab.example.org", address="127.0.0.1", port=port)
        return SNMP(device)


class TestSNMPRequestsResponseTypes(TestSNMPRequests):
    @pytest.mark.asyncio
    async def test_get(self, snmpsim, snmp_test_port):
        snmp = self.get_client(snmp_test_port)
        response = await snmp.get("SNMPv2-MIB", "sysUpTime", 0)
        assert isinstance(response.oid, str)
        assert isinstance(response.value, int)

    @pytest.mark.asyncio
    async def test_getnext(self, snmpsim, snmp_test_port):
        snmp = self.get_client(snmp_test_port)
        response = await snmp.getnext("SNMPv2-MIB", "sysUpTime")
        assert isinstance(response.oid, str)
        assert isinstance(response.value, int)

    @pytest.mark.asyncio
    async def test_walk(self, snmpsim, snmp_test_port):
        snmp = self.get_client(snmp_test_port)
        response = await snmp.walk("SNMPv2-MIB", "sysUpTime")
        assert response
        for mibobject in response:
            assert isinstance(mibobject.oid, str)
            assert isinstance(mibobject.value, int)

    @pytest.mark.asyncio
    async def test_getbulk(self, snmpsim, snmp_test_port):
        snmp = self.get_client(snmp_test_port)
        response = await snmp.getbulk("SNMPv2-MIB", "sysUpTime")
        assert response
        for mibobject in response:
            assert isinstance(mibobject.oid, str)
            assert isinstance(mibobject.value, int)

    @pytest.mark.asyncio
    async def test_bulkwalk(self, snmpsim, snmp_test_port):
        snmp = self.get_client(snmp_test_port)
        response = await snmp.bulkwalk("SNMPv2-MIB", "sysUpTime")
        assert response
        for mibobject in response:
            assert isinstance(mibobject.oid, str)
            assert isinstance(mibobject.value, int)


class TestSNMPRequestsUnknownMib(TestSNMPRequests):
    @pytest.mark.asyncio
    async def test_get(self, snmpsim, snmp_test_port):
        snmp = self.get_client(snmp_test_port)
        response = await snmp.get("fake", "mib")
        assert not response

    @pytest.mark.asyncio
    async def test_getnext(self, snmpsim, snmp_test_port):
        snmp = self.get_client(snmp_test_port)
        response = await snmp.getnext("fake", "mib")
        assert not response

    @pytest.mark.asyncio
    async def test_walk(self, snmpsim, snmp_test_port):
        snmp = self.get_client(snmp_test_port)
        response = await snmp.walk("fake", "mib")
        assert not response

    @pytest.mark.asyncio
    async def test_getbulk(self, snmpsim, snmp_test_port):
        snmp = self.get_client(snmp_test_port)
        response = await snmp.getbulk("fake", "mib")
        assert not response

    @pytest.mark.asyncio
    async def test_bulkwalk(self, snmpsim, snmp_test_port):
        snmp = self.get_client(snmp_test_port)
        response = await snmp.bulkwalk("fake", "mib")
        assert not response


class TestPrefix:
    def test_return_true_if_prefix(self):
        is_prefix = SNMP._is_prefix_of_oid("1.2.3.4.5", "1.2.3.4.5.6")
        assert is_prefix

    def test_return_false_if_not_prefix(self):
        is_prefix = SNMP._is_prefix_of_oid("5.4.3.2.1", "1.2.3.4.5.6")
        assert not is_prefix

    def test_return_false_if_prefix_equal_to_oid(self):
        is_prefix = SNMP._is_prefix_of_oid("5.4.3.2.1", "5.4.3.2.1")
        assert not is_prefix


def test_object_is_resolved():
    objecttype = SNMP._oid_to_objecttype("SNMPv2-MIB", "sysUpTime")
    SNMP._resolve_object(objecttype)
    assert objecttype[0]


def test_object_with_pure_oid_is_resolved():
    objecttype = SNMP._oid_to_objecttype("1.3.6.1.2.1.1.3.0")
    SNMP._resolve_object(objecttype)
    assert objecttype[0]
