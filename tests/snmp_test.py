import pytest

from zino.config.models import PollDevice
from zino.oid import OID
from zino.snmp import SNMP


@pytest.fixture(scope="session")
def snmp_client(snmpsim, snmp_test_port):
    device = PollDevice(name="buick.lab.example.org", address="127.0.0.1", port=snmp_test_port)
    return SNMP(device)


class TestSNMPRequestsResponseTypes:
    @pytest.mark.asyncio
    async def test_get(self, snmp_client):
        response = await snmp_client.get("SNMPv2-MIB", "sysUpTime", 0)
        assert isinstance(response.oid, OID)
        assert isinstance(response.value, int)

    @pytest.mark.asyncio
    async def test_getnext(self, snmp_client):
        response = await snmp_client.getnext("SNMPv2-MIB", "sysUpTime")
        assert isinstance(response.oid, OID)
        assert isinstance(response.value, int)

    @pytest.mark.asyncio
    async def test_walk(self, snmp_client):
        response = await snmp_client.walk("SNMPv2-MIB", "sysUpTime")
        assert response
        for mib_object in response:
            assert isinstance(mib_object.oid, OID)
            assert isinstance(mib_object.value, int)

    @pytest.mark.asyncio
    async def test_getbulk(self, snmp_client):
        response = await snmp_client.getbulk("SNMPv2-MIB", "sysUpTime")
        assert response
        for mib_object in response:
            assert isinstance(mib_object.oid, OID)
            assert isinstance(mib_object.value, int)

    @pytest.mark.asyncio
    async def test_bulkwalk(self, snmp_client):
        response = await snmp_client.bulkwalk("SNMPv2-MIB", "sysUpTime")
        assert response
        for mib_object in response:
            assert isinstance(mib_object.oid, OID)
            assert isinstance(mib_object.value, int)

    @pytest.mark.asyncio
    async def test_get_sysobjectid_should_be_tuple_of_ints(self, snmp_client):
        response = await snmp_client.get("SNMPv2-MIB", "sysObjectID", 0)
        assert isinstance(response.oid, OID)
        assert isinstance(response.value, OID)
        assert all(isinstance(i, int) for i in response.value)


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


def test_object_is_resolved():
    object_type = SNMP._oid_to_object_type("SNMPv2-MIB", "sysUpTime")
    SNMP._resolve_object(object_type)
    assert object_type[0]
