import asyncio
from unittest.mock import Mock, patch

import pytest
from pysnmp.hlapi.asyncio import Udp6TransportTarget, UdpTransportTarget
from pysnmp.proto import errind

from zino.config.models import PollDevice
from zino.oid import OID
from zino.snmp import SNMP, Identifier, MibNotFoundError, NoSuchNameError


@pytest.fixture(scope="session")
def snmp_client(snmpsim, snmp_test_port):
    device = PollDevice(name="buick.lab.example.org", address="127.0.0.1", port=snmp_test_port)
    return SNMP(device)


@pytest.fixture(scope="session")
def ipv6_snmp_client(snmpsim, snmp_test_port) -> SNMP:
    device = PollDevice(name="buick.lab.example.org", address="::1", port=snmp_test_port)
    return SNMP(device)


@pytest.fixture(scope="session")
def unreachable_snmp_client():
    mock_results = errind.RequestTimedOut(), None, None, []
    future = asyncio.Future()
    future.set_result(mock_results)
    timeout_mock = Mock(return_value=future)
    with patch.multiple("zino.snmp", getCmd=timeout_mock, nextCmd=timeout_mock, bulkCmd=timeout_mock):
        device = PollDevice(name="nonexist", address="127.0.0.1", community="invalid", port=666, timeout=1, retries=0)
        yield SNMP(device)


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
    async def test_getnext2_should_return_symbolic_identifiers(self, snmp_client):
        response = await snmp_client.getnext2(("IF-MIB", "ifName", "1"), ("IF-MIB", "ifAlias", "1"))
        assert len(list(response)) == 2
        assert any(identifier == Identifier("IF-MIB", "ifName", OID(".2")) for identifier, _ in response)
        assert any(identifier == Identifier("IF-MIB", "ifAlias", OID(".2")) for identifier, _ in response)

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
    async def test_getbulk2_should_have_expected_response(self, snmp_client):
        variables = ("ifIndex", "ifDescr", "ifAlias")
        response = await snmp_client.getbulk2(*(("IF-MIB", var) for var in variables))
        assert response
        for var_binds in response:
            assert len(var_binds) == len(variables)
            for ident, value in var_binds:
                assert ident.object in variables

    @pytest.mark.asyncio
    async def test_bulkwalk(self, snmp_client):
        response = await snmp_client.bulkwalk("SNMPv2-MIB", "sysUpTime")
        assert response
        for mib_object in response:
            assert isinstance(mib_object.oid, OID)
            assert isinstance(mib_object.value, int)

    @pytest.mark.asyncio
    async def test_sparsewalk_should_have_expected_response(self, snmp_client):
        variables = ("ifIndex", "ifDescr", "ifAlias")
        response = await snmp_client.sparsewalk(*(("IF-MIB", var) for var in variables))
        assert response
        for index, row in response.items():
            assert isinstance(index, OID)
            assert isinstance(row, dict)
            for var, val in row.items():
                assert var in variables

    @pytest.mark.asyncio
    async def test_get_sysobjectid_should_be_tuple_of_ints(self, snmp_client):
        response = await snmp_client.get("SNMPv2-MIB", "sysObjectID", 0)
        assert isinstance(response.oid, OID)
        assert isinstance(response.value, OID)
        assert all(isinstance(i, int) for i in response.value)

    @pytest.mark.asyncio
    async def test_get_named_value_should_return_symbolic_name(self, snmp_client):
        response = await snmp_client.getnext("SNMPv2-MIB", "snmpEnableAuthenTraps")
        assert response.value == "disabled"


class TestUnknownMibShouldRaiseException:
    @pytest.mark.asyncio
    async def test_get(self, snmp_client):
        with pytest.raises(MibNotFoundError):
            await snmp_client.get("NON-EXISTENT-MIB", "foo", 0)

    @pytest.mark.asyncio
    async def test_getnext(self, snmp_client):
        with pytest.raises(MibNotFoundError):
            await snmp_client.getnext("NON-EXISTENT-MIB", "foo")

    @pytest.mark.asyncio
    async def test_getnext2(self, snmp_client):
        with pytest.raises(MibNotFoundError):
            await snmp_client.getnext2(("NON-EXISTENT-MIB", "foo"))

    @pytest.mark.asyncio
    async def test_walk(self, snmp_client):
        with pytest.raises(MibNotFoundError):
            await snmp_client.walk("NON-EXISTENT-MIB", "foo")

    @pytest.mark.asyncio
    async def test_getbulk(self, snmp_client):
        with pytest.raises(MibNotFoundError):
            await snmp_client.getbulk("NON-EXISTENT-MIB", "foo")

    @pytest.mark.asyncio
    async def test_bulkwalk(self, snmp_client):
        with pytest.raises(MibNotFoundError):
            await snmp_client.bulkwalk("NON-EXISTENT-MIB", "foo")

    @pytest.mark.asyncio
    async def test_getbulk2(self, snmp_client):
        with pytest.raises(MibNotFoundError):
            await snmp_client.getbulk2(("NON-EXISTENT-MIB", "foo"))

    @pytest.mark.asyncio
    async def test_sparsewalk(self, snmp_client):
        with pytest.raises(MibNotFoundError):
            await snmp_client.sparsewalk(("NON-EXISTENT-MIB", "foo"))


class TestMibResolver:
    """Tests to ensure that various required MIBs can be resolved"""

    def test_sysuptime_should_be_resolved(self):
        object_type = SNMP._oid_to_object_type("SNMPv2-MIB", "sysUpTime")
        SNMP._resolve_object(object_type)
        assert object_type[0]

    def test_ifalias_should_be_resolved(self):
        object_type = SNMP._oid_to_object_type("IF-MIB", "ifAlias", "1")
        SNMP._resolve_object(object_type)
        assert object_type[0]


class TestUnreachableDeviceShouldRaiseException:
    @pytest.mark.asyncio
    async def test_get(self, unreachable_snmp_client):
        with pytest.raises(TimeoutError):
            await unreachable_snmp_client.get("SNMPv2-MIB", "sysUpTime", 0)

    @pytest.mark.asyncio
    async def test_getnext(self, unreachable_snmp_client):
        with pytest.raises(TimeoutError):
            await unreachable_snmp_client.getnext("SNMPv2-MIB", "sysUpTime")

    @pytest.mark.asyncio
    async def test_getnext2(self, unreachable_snmp_client):
        with pytest.raises(TimeoutError):
            await unreachable_snmp_client.getnext2(("SNMPv2-MIB", "sysUpTime"))

    @pytest.mark.asyncio
    async def test_walk(self, unreachable_snmp_client):
        with pytest.raises(TimeoutError):
            await unreachable_snmp_client.walk("SNMPv2-MIB", "sysUpTime")

    @pytest.mark.asyncio
    async def test_getbulk(self, unreachable_snmp_client):
        with pytest.raises(TimeoutError):
            await unreachable_snmp_client.getbulk("SNMPv2-MIB", "sysUpTime")

    @pytest.mark.asyncio
    async def test_bulkwalk(self, unreachable_snmp_client):
        with pytest.raises(TimeoutError):
            await unreachable_snmp_client.bulkwalk("SNMPv2-MIB", "sysUpTime")

    @pytest.mark.asyncio
    async def test_getbulk2(self, unreachable_snmp_client):
        with pytest.raises(TimeoutError):
            await unreachable_snmp_client.getbulk2(("SNMPv2-MIB", "sysUpTime"))

    @pytest.mark.asyncio
    async def test_sparsewalk(self, unreachable_snmp_client):
        with pytest.raises(TimeoutError):
            await unreachable_snmp_client.sparsewalk(("SNMPv2-MIB", "sysUpTime"))


@pytest.mark.asyncio
async def test_get_object_that_does_not_exist_should_raise_exception(snmp_client):
    with pytest.raises(NoSuchNameError):
        await snmp_client.get("SNMPv2-MIB", "sysUpTime", 1)


class TestUdpTransportTarget:
    def test_when_device_address_is_ipv6_then_udp6_transport_should_be_returned(self, ipv6_snmp_client):
        assert isinstance(ipv6_snmp_client.udp_transport_target, Udp6TransportTarget)

    def test_when_device_address_is_ipv4_then_udp_transport_should_be_returned(self, snmp_client):
        assert isinstance(snmp_client.udp_transport_target, UdpTransportTarget)
