import logging
from ipaddress import ip_address
from unittest.mock import Mock

import pytest

from zino.oid import OID
from zino.trapd.base import TrapMessage
from zino.trapobservers.logged_traps import (
    CiscoConfigManEventLogger,
    CiscoPimTrapLogger,
    CiscoReloadTrapLogger,
    OspfIfConfigErrorLogger,
    RestartTrapLogger,
)


class TestRestartTrapLogger:
    @pytest.mark.parametrize("trap_name", ["coldStart", "warmStart"])
    async def test_when_handle_trap_is_called_it_should_log_trap_name(
        self, caplog, localhost_trap_originator, trap_name
    ):
        observer = RestartTrapLogger(state=Mock())
        trap = TrapMessage(agent=localhost_trap_originator, mib="SNMPv2-MIB", name=trap_name)
        with caplog.at_level(logging.INFO):
            await observer.handle_trap(trap=trap)
            assert f"localhost: {trap_name}" in caplog.text


class TestCiscoReloadTrapLogger:
    async def test_when_handle_trap_is_called_it_should_log_reload(
        self,
        caplog,
        localhost_trap_originator,
    ):
        observer = CiscoReloadTrapLogger(state=Mock())
        trap = TrapMessage(agent=localhost_trap_originator, mib="CISCOTRAP-MIB", name="reload")
        with caplog.at_level(logging.INFO):
            await observer.handle_trap(trap=trap)
            assert "localhost: reload requested" in caplog.text


class TestCiscoConfigManEventLogger:
    async def test_when_handle_trap_is_called_it_should_log_config_change(
        self,
        caplog,
        localhost_trap_originator,
    ):
        observer = CiscoConfigManEventLogger(state=Mock())
        trap = TrapMessage(
            agent=localhost_trap_originator,
            mib="CISCO-CONFIG-MAN",
            name="ciscoConfigManEvent",
            variables=[
                Mock(var="ccmHistoryEventCommandSource", value="snmp"),
                Mock(var="ccmHistoryEventConfigSource", value="networkTftp"),
                Mock(var="ccmHistoryEventConfigDestination", value="startup"),
            ],
        )
        with caplog.at_level(logging.INFO):
            await observer.handle_trap(trap=trap)
            assert "localhost: config-change: cmd-src snmp conf-src networkTftp dst startup" in caplog.text


class TestCiscoPimTrapLogger:
    async def test_when_handle_trap_is_called_with_invalid_pim_register_it_should_log_it_correctly(
        self, caplog, localhost_trap_originator
    ):
        observer = CiscoPimTrapLogger(state=Mock())
        trap = TrapMessage(
            agent=localhost_trap_originator,
            mib="CISCO-PIM-MIB",
            name="ciscoPimInvalidRegister",
            variables=[
                Mock(var="cpimLastErrorOriginType", value="ipv4"),
                Mock(var="cpimLastErrorOrigin", raw_value=b"\x0a\x00\x00\x01"),
                Mock(var="cpimLastErrorGroupType", value="ipv4"),
                Mock(var="cpimLastErrorGroup", raw_value=b"\x0a\x00\x00\x02"),
                Mock(var="cpimLastErrorRPType", value="ipv4"),
                Mock(var="cpimLastErrorRP", raw_value=b"\x0a\x00\x00\x03"),
                Mock(var="cpimInvalidRegisterMsgsRcvd", value=42),
            ],
        )
        with caplog.at_level(logging.INFO):
            await observer.handle_trap(trap=trap)
            assert "localhost PIM-invalid-register: from 10.0.0.1 group 10.0.0.2 RP 10.0.0.3" in caplog.text

    async def test_when_trap_is_missing_error_origin_type_it_should_ignore_it(self, caplog, localhost_trap_originator):
        observer = CiscoPimTrapLogger(state=Mock())
        trap = TrapMessage(
            agent=localhost_trap_originator,
            mib="CISCO-PIM-MIB",
            name="ciscoPimInvalidRegister",
            variables=[
                Mock(var="cpimLastErrorOrigin", raw_value=b"\x0a\x00\x00\x01"),
                Mock(var="cpimLastErrorGroupType", value="ipv4"),
                Mock(var="cpimLastErrorGroup", raw_value=b"\x0a\x00\x00\x02"),
                Mock(var="cpimLastErrorRPType", value="ipv4"),
                Mock(var="cpimLastErrorRP", raw_value=b"\x0a\x00\x00\x03"),
                Mock(var="cpimInvalidRegisterMsgsRcvd", value=42),
            ],
        )
        with caplog.at_level(logging.INFO):
            await observer.handle_trap(trap=trap)
            assert "PIM-invalid" not in caplog.text

    async def test_when_trap_error_origin_type_is_not_ipv4_it_should_ignore_it(self, caplog, localhost_trap_originator):
        observer = CiscoPimTrapLogger(state=Mock())
        trap = TrapMessage(
            agent=localhost_trap_originator,
            mib="CISCO-PIM-MIB",
            name="ciscoPimInvalidRegister",
            variables=[
                Mock(var="cpimLastErrorOriginType", value="ipv6"),
                Mock(var="cpimLastErrorOrigin", raw_value=b"\x0a\x00\x00\x01"),
                Mock(var="cpimLastErrorGroupType", value="ipv4"),
                Mock(var="cpimLastErrorGroup", raw_value=b"\x0a\x00\x00\x02"),
                Mock(var="cpimLastErrorRPType", value="ipv4"),
                Mock(var="cpimLastErrorRP", raw_value=b"\x0a\x00\x00\x03"),
                Mock(var="cpimInvalidRegisterMsgsRcvd", value=42),
            ],
        )
        with caplog.at_level(logging.INFO):
            await observer.handle_trap(trap=trap)
            assert "PIM-invalid" not in caplog.text


class TestOspfIfConfigErrorLogger:
    async def test_when_handle_trap_is_called_with_ospf_config_error_it_should_log_it_correctly(
        self, caplog, localhost_trap_originator
    ):
        observer = OspfIfConfigErrorLogger(state=Mock())
        snmp_trap_oid = OID(".1.3.6.1.2.1.14.16.2.4")
        trap = TrapMessage(
            agent=localhost_trap_originator,
            mib="OSPF-MIB",
            name="ospfIfConfigError",
            variables=[
                Mock(var="snmpTrapOID", value=snmp_trap_oid),
                Mock(var="ospfRouterId", raw_value=b"\x0a\x00\x00\x01", value=ip_address("10.0.0.1")),
                Mock(var="ospfIfIpAddress", raw_value=b"\xc0\xa8\x01\x01", value=ip_address("192.168.1.1")),
                Mock(var="doesNotBelongValue", value="foobar"),
            ],
        )
        with caplog.at_level(logging.INFO):
            await observer.handle_trap(trap=trap)

        assert f"localhost: trap {snmp_trap_oid}" in caplog.text
        assert "localhost: trap-var ospfRouterId: 10.0.0.1" in caplog.text
        assert "localhost: trap-var ospfIfIpAddress: 192.168.1.1" in caplog.text
        assert "doesNotBelongValue" not in caplog.text
