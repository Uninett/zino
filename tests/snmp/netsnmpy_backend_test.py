import asyncio
import os
from unittest.mock import Mock, patch

import pytest
from netsnmpy import netsnmp
from netsnmpy.netsnmp import EndOfMibView, NoSuchInstance, NoSuchObject, SNMPVariable
from netsnmpy.oids import OID

from zino.config.models import PollDevice
from zino.snmp.base import (
    EndOfMibViewError,
    Identifier,
    MibNotFoundError,
    NoSuchInstanceError,
    NoSuchNameError,
    NoSuchObjectError,
    SNMPBackendError,
    SNMPBackendVersionError,
)
from zino.snmp.netsnmpy_backend import SNMP, init_backend, resolve_symbol


@pytest.fixture(scope="session")
def snmp_client(snmpsim, snmp_test_port):
    device = PollDevice(name="buick.lab.example.org", address="127.0.0.1", port=snmp_test_port)
    with SNMP(device) as snmp:
        yield snmp


@pytest.fixture(scope="session")
def ipv6_snmp_client(snmpsim, snmp_test_port) -> SNMP:
    device = PollDevice(name="buick.lab.example.org", address="::1", port=snmp_test_port)
    return SNMP(device)


@pytest.fixture()
def unreachable_snmp_client():
    future = asyncio.Future()
    future.set_exception(TimeoutError("Mock timeout"))
    timeout_mock = Mock(return_value=future)
    with patch.multiple(
        "zino.snmp.netsnmpy_backend.SNMP",
        get=timeout_mock,
        getnext=timeout_mock,
        getnext2=timeout_mock,
        walk=timeout_mock,
        getbulk=timeout_mock,
        bulkwalk=timeout_mock,
        getbulk2=timeout_mock,
        sparsewalk=timeout_mock,
    ):
        device = PollDevice(name="nonexist", address="127.0.0.1", community="invalid", port=666)
        yield SNMP(device)


class TestInitBackend:
    def test_when_netsnmp_is_too_old_it_should_raise(self):
        with patch("zino.snmp.netsnmpy_backend.netsnmp.get_version", return_value=(5, 7, 0)):
            with pytest.raises(SNMPBackendVersionError):
                init_backend()

    def test_when_mibdirs_envvar_is_not_set_it_should_set_it(self):
        env = os.environ.copy()
        env.pop("MIBDIRS", None)
        with patch("os.environ", env):
            init_backend()
            assert "MIBDIRS" in os.environ

    def test_when_vendored_mib_cannot_be_resolved_it_should_raise(self):
        with patch("zino.snmp.netsnmpy_backend.netsnmp.symbol_to_oid", side_effect=ValueError("Mock error")):
            with pytest.raises(SNMPBackendError):
                init_backend()


class TestSNMPRequestsResponseTypes:

    async def test_get(self, snmp_client):
        response = await snmp_client.get("SNMPv2-MIB", "sysUpTime", 0)
        assert isinstance(response.oid, OID)
        assert isinstance(response.value, int)

    async def test_get2_should_return_symbolic_identifiers(self, snmp_client):
        response = await snmp_client.get2(("IF-MIB", "ifName", 1), ("IF-MIB", "ifAlias", 1))
        assert len(list(response)) == 2
        assert any(identifier == Identifier("IF-MIB", "ifName", OID(".1")) for identifier, _ in response)
        assert any(identifier == Identifier("IF-MIB", "ifAlias", OID(".1")) for identifier, _ in response)

    async def test_when_mib_is_unkown_get2_should_raise_mibnotfounderror(self, snmp_client):
        with pytest.raises(MibNotFoundError):
            await snmp_client.get2(("FOOBAR-MIB", "ifName", 1), ("FOOBAR-MIB", "ifAlias", 1))

    async def test_getnext(self, snmp_client):
        response = await snmp_client.getnext("SNMPv2-MIB", "sysUpTime")
        assert isinstance(response.oid, OID)
        assert isinstance(response.value, int)

    async def test_getnext2_should_return_symbolic_identifiers(self, snmp_client):
        response = await snmp_client.getnext2(("IF-MIB", "ifName", "1"), ("IF-MIB", "ifAlias", "1"))
        assert len(list(response)) == 2
        assert any(identifier == Identifier("IF-MIB", "ifName", OID(".2")) for identifier, _ in response)
        assert any(identifier == Identifier("IF-MIB", "ifAlias", OID(".2")) for identifier, _ in response)

    async def test_walk(self, snmp_client):
        response = await snmp_client.walk("SNMPv2-MIB", "sysUpTime")
        assert response
        for mib_object in response:
            assert isinstance(mib_object.oid, OID)
            assert isinstance(mib_object.value, int)

    async def test_getbulk(self, snmp_client):
        response = await snmp_client.getbulk("SNMPv2-MIB", "sysUpTime")
        assert response
        for mib_object in response:
            assert isinstance(mib_object.oid, OID)
            assert isinstance(mib_object.value, int)

    async def test_getbulk2_should_have_expected_response(self, snmp_client):
        variables = ("ifIndex", "ifDescr", "ifAlias")
        response = await snmp_client.getbulk2(*(("IF-MIB", var) for var in variables))
        assert response
        for var_binds in response:
            assert len(var_binds) == len(variables)
            for ident, value in var_binds:
                assert ident.object in variables

    async def test_bulkwalk(self, snmp_client):
        response = await snmp_client.bulkwalk("SNMPv2-MIB", "sysUpTime")
        assert response
        for mib_object in response:
            assert isinstance(mib_object.oid, OID)
            assert isinstance(mib_object.value, int)

    async def test_sparsewalk_should_have_expected_response(self, snmp_client):
        variables = ("ifIndex", "ifDescr", "ifAlias")
        response = await snmp_client.sparsewalk(*(("IF-MIB", var) for var in variables))
        assert response
        for index, row in response.items():
            assert isinstance(index, OID)
            assert isinstance(row, dict)
            for var, val in row.items():
                assert var in variables

    async def test_get_sysobjectid_should_be_tuple_of_ints(self, snmp_client):
        response = await snmp_client.get("SNMPv2-MIB", "sysObjectID", 0)
        assert isinstance(response.oid, OID)
        assert isinstance(response.value, OID)
        assert all(isinstance(i, int) for i in response.value)

    async def test_get_named_value_should_return_symbolic_name(self, snmp_client):
        response = await snmp_client.getnext("SNMPv2-MIB", "snmpEnableAuthenTraps")
        assert response.value == "disabled"


class TestUnknownMibShouldRaiseException:

    async def test_get(self, snmp_client):
        with pytest.raises(MibNotFoundError):
            await snmp_client.get("NON-EXISTENT-MIB", "foo", 0)

    async def test_getnext(self, snmp_client):
        with pytest.raises(MibNotFoundError):
            await snmp_client.getnext("NON-EXISTENT-MIB", "foo")

    async def test_getnext2(self, snmp_client):
        with pytest.raises(MibNotFoundError):
            await snmp_client.getnext2(("NON-EXISTENT-MIB", "foo"))

    async def test_walk(self, snmp_client):
        with pytest.raises(MibNotFoundError):
            await snmp_client.walk("NON-EXISTENT-MIB", "foo")

    async def test_getbulk(self, snmp_client):
        with pytest.raises(MibNotFoundError):
            await snmp_client.getbulk("NON-EXISTENT-MIB", "foo")

    async def test_bulkwalk(self, snmp_client):
        with pytest.raises(MibNotFoundError):
            await snmp_client.bulkwalk("NON-EXISTENT-MIB", "foo")

    async def test_getbulk2(self, snmp_client):
        with pytest.raises(MibNotFoundError):
            await snmp_client.getbulk2(("NON-EXISTENT-MIB", "foo"))

    async def test_sparsewalk(self, snmp_client):
        with pytest.raises(MibNotFoundError):
            await snmp_client.sparsewalk(("NON-EXISTENT-MIB", "foo"))


class TestMibResolver:
    """Tests to ensure that various required MIBs can be resolved"""

    def test_sysuptime_should_be_resolved(self):
        assert resolve_symbol(("SNMPv2-MIB", "sysUpTime"))

    def test_ifalias_should_be_resolved(self):
        assert resolve_symbol(("IF-MIB", "ifAlias", "1"))

    def test_ipadentaddr_should_be_resolved(self):
        assert resolve_symbol(("IP-MIB", "ipAdEntAddr"))

    def test_jnx_bgp_m2_peer_state_should_be_resolved(self):
        assert resolve_symbol(("BGP4-V2-MIB-JUNIPER", "jnxBgpM2PeerState"))

    def test_c_bgp_peer2_state_should_be_resolved(self):
        assert resolve_symbol(("CISCO-BGP4-MIB", "cbgpPeer2State"))

    def test_bgp_peer_state_should_be_resolved(self):
        assert resolve_symbol(("BGP4-MIB", "bgpPeerState"))

    def test_juniper_bgp_mib_oids_should_be_resolved_to_symbols(self):
        """Ensure vendored MIBs are loaded properly by testing low-level netsnmpy lookup"""
        oid = OID(
            ".1.3.6.1.4.1.2636.5.1.1.2.1.1.1.11.0.2.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.2.32.1.7.0.0.0.128.1.0.0.0.0.0.0.0.2"
        )
        symbol = netsnmp.oid_to_symbol(oid)
        assert symbol.startswith("BGP4-V2-MIB-JUNIPER::jnxBgpM2PeerRemoteAddr")


class TestUnreachableDeviceShouldRaiseException:

    async def test_get(self, unreachable_snmp_client):
        with pytest.raises(TimeoutError):
            await unreachable_snmp_client.get("SNMPv2-MIB", "sysUpTime", 0)

    async def test_getnext(self, unreachable_snmp_client):
        with pytest.raises(TimeoutError):
            await unreachable_snmp_client.getnext("SNMPv2-MIB", "sysUpTime")

    async def test_getnext2(self, unreachable_snmp_client):
        with pytest.raises(TimeoutError):
            await unreachable_snmp_client.getnext2(("SNMPv2-MIB", "sysUpTime"))

    async def test_walk(self, unreachable_snmp_client):
        with pytest.raises(TimeoutError):
            await unreachable_snmp_client.walk("SNMPv2-MIB", "sysUpTime")

    async def test_getbulk(self, unreachable_snmp_client):
        with pytest.raises(TimeoutError):
            await unreachable_snmp_client.getbulk("SNMPv2-MIB", "sysUpTime")

    async def test_bulkwalk(self, unreachable_snmp_client):
        with pytest.raises(TimeoutError):
            await unreachable_snmp_client.bulkwalk("SNMPv2-MIB", "sysUpTime")

    async def test_getbulk2(self, unreachable_snmp_client):
        with pytest.raises(TimeoutError):
            await unreachable_snmp_client.getbulk2(("SNMPv2-MIB", "sysUpTime"))

    async def test_sparsewalk(self, unreachable_snmp_client):
        with pytest.raises(TimeoutError):
            await unreachable_snmp_client.sparsewalk(("SNMPv2-MIB", "sysUpTime"))


async def test_get_object_that_does_not_exist_should_raise_exception(snmp_client):
    with pytest.raises((NoSuchNameError, NoSuchInstanceError)):
        # NoSuchNameError is only relevant on SNMP v1, for v2c the error is NoSuchInstanceError
        await snmp_client.get("SNMPv2-MIB", "sysUpTime", 1)


class TestVarBindErrors:
    """
    Test class for verifying the handling of varbind errors in SNMP commands.

    This class contains tests that check if the correct exceptions are raised when
    varbind errors (NoSuchObject, NoSuchInstance, EndOfMibView) are encountered
    in the response to an SNMP command.
    """

    @pytest.mark.parametrize(
        "error, exception",
        [
            (NoSuchObject(""), NoSuchObjectError),
            (NoSuchInstance(""), NoSuchInstanceError),
            (EndOfMibView(""), EndOfMibViewError),
        ],
        ids=["NoSuchObject-NoSuchObjectError", "NoSuchInstance-NoSuchInstanceError", "EndOfMibView-EndOfMibViewError"],
    )
    async def test_get_should_raise_exception(self, error, exception, snmp_client, monkeypatch):
        query = ("SNMPv2-MIB", "sysDescr", 0)
        oid = resolve_symbol(query)
        mock_results = [SNMPVariable(oid, error)]
        future = asyncio.Future()
        future.set_result(mock_results)
        get_mock = Mock(return_value=future)
        monkeypatch.setattr("zino.snmp.netsnmpy_backend.SNMPSession.aget", get_mock)

        with pytest.raises(exception):
            await snmp_client.get(*query)
