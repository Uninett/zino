import pytest

from zino.config.models import PollDevice
from zino.snmp import SNMP


@pytest.fixture(scope="session")
def snmp_client(snmpsim, snmp_test_port):
    device = PollDevice(name="buick.lab.example.org", address="127.0.0.1", port=snmp_test_port)
    return SNMP(device)


class TestSNMPRequestsResponseTypes:
    @pytest.mark.asyncio
    async def test_get(self, snmp_client):
        response = await snmp_client.get("SNMPv2-MIB", "sysUpTime", 0)
        assert isinstance(response.oid, str)
        assert isinstance(response.value, int)

    @pytest.mark.asyncio
    async def test_getnext(self, snmp_client):
        response = await snmp_client.getnext("SNMPv2-MIB", "sysUpTime")
        assert isinstance(response.oid, str)
        assert isinstance(response.value, int)

    @pytest.mark.asyncio
    async def test_walk(self, snmp_client):
        response = await snmp_client.walk("SNMPv2-MIB", "sysUpTime")
        assert response
        for mibobject in response:
            assert isinstance(mibobject.oid, str)
            assert isinstance(mibobject.value, int)

    @pytest.mark.asyncio
    async def test_getbulk(self, snmp_client):
        response = await snmp_client.getbulk("SNMPv2-MIB", "sysUpTime")
        assert response
        for mibobject in response:
            assert isinstance(mibobject.oid, str)
            assert isinstance(mibobject.value, int)

    @pytest.mark.asyncio
    async def test_bulkwalk(self, snmp_client):
        response = await snmp_client.bulkwalk("SNMPv2-MIB", "sysUpTime")
        assert response
        for mibobject in response:
            assert isinstance(mibobject.oid, str)
            assert isinstance(mibobject.value, int)


class TestSNMPRequestsUnknownMib:
    @pytest.mark.asyncio
    async def test_get(self, snmp_client):
        response = await snmp_client.get("fake", "mib")
        assert not response

    @pytest.mark.asyncio
    async def test_getnext(self, snmp_client):
        response = await snmp_client.getnext("fake", "mib")
        assert not response

    @pytest.mark.asyncio
    async def test_walk(self, snmp_client):
        response = await snmp_client.walk("fake", "mib")
        assert not response

    @pytest.mark.asyncio
    async def test_getbulk(self, snmp_client):
        response = await snmp_client.getbulk("fake", "mib")
        assert not response

    @pytest.mark.asyncio
    async def test_bulkwalk(self, snmp_client):
        response = await snmp_client.bulkwalk("fake", "mib")
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
