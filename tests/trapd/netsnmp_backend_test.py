import ipaddress
import logging
import shutil
from collections import Counter
from unittest.mock import Mock, patch

import pytest
from netsnmpy.netsnmp import SNMPVariable
from netsnmpy.oids import OID as NS_OID
from netsnmpy.trapsession import SNMPTrap

from zino.oid import OID
from zino.trapd.base import (
    TrapMessage,
    TrapObserver,
    TrapOriginator,
    TrapVarBind,
)
from zino.trapd.netsnmpy_backend import TrapReceiver

from . import send_trap_externally

OID_COLD_START = ".1.3.6.1.6.3.1.1.5.1"
OID_SYSNAME_0 = ".1.3.6.1.2.1.1.5.0"


class TestTrapReceiver:
    async def test_add_community_should_accept_same_community_multiple_times(self):
        receiver = TrapReceiver()
        receiver.add_community("public")
        receiver.add_community("public")
        assert len(receiver._communities) == 1

    async def test_when_trap_lacks_trap_oid_it_should_be_ignored(self, localhost_netsnmpy_receiver):
        origin = TrapOriginator(address=ipaddress.ip_address("127.0.0.1"), port=666)
        trap = TrapMessage(agent=origin)
        trap.variables.append(
            TrapVarBind(
                oid=OID(".1.3.6.1.2.1.1.3.0"),
                mib="SNMPv2-MIB",
                var="sysUpTime",
                instance=OID(".0"),
                raw_value=None,
                value=123,
            )
        )
        assert not localhost_netsnmpy_receiver._verify_trap(trap, origin)

    async def test_when_trap_lacks_sysuptime_it_should_be_ignored(self, localhost_netsnmpy_receiver):
        origin = TrapOriginator(address=ipaddress.ip_address("127.0.0.1"), port=666)
        trap = TrapMessage(agent=origin)
        trap.variables.append(
            TrapVarBind(
                oid=OID(".1.3.6.1.6.3.1.1.4.1"),
                mib="SNMPv2-MIB",
                var="snmpTrapOID",
                instance=None,
                raw_value=OID(".1.1.1"),
                value=("FAKE-MIB", "fakeTrap"),
            )
        )
        assert not localhost_netsnmpy_receiver._verify_trap(trap, origin)

    async def test_when_trap_observer_wants_no_traps_auto_subscribe_should_ignore_it(self, localhost_netsnmpy_receiver):
        class MockObserver(TrapObserver):
            WANTED_TRAPS = set()

        localhost_netsnmpy_receiver.auto_subscribe_observers()
        assert not any(
            isinstance(observer, MockObserver) for observer in localhost_netsnmpy_receiver._observers.values()
        )

    async def test_when_called_multiple_times_auto_subscribe_should_not_add_duplicates(
        self, localhost_netsnmpy_receiver
    ):
        """The same observer class should not be subscribed more than once for the same trap"""

        class MockObserver(TrapObserver):
            WANTED_TRAPS = {("MOCK-MIB", "mockTrap")}

        localhost_netsnmpy_receiver.auto_subscribe_observers()
        localhost_netsnmpy_receiver.auto_subscribe_observers()

        type_counts = Counter(
            (trap, type(observer))
            for trap, observers in localhost_netsnmpy_receiver._observers.items()
            for observer in observers
        )
        dupes = {ident: count for ident, count in type_counts.items() if count > 1}
        assert not dupes

    async def test_when_trap_is_unknown_it_should_not_crash(self, localhost_netsnmpy_receiver):
        source = ipaddress.ip_address("127.0.0.1")
        trap = SNMPTrap(
            source=source,
            agent=source,
            generic_type=None,
            trap_oid=OID(".1.1.1.1.1.1.1.1"),
            uptime=1984,
            community="public",
            version="2c",
            variables=[
                SNMPVariable(NS_OID(".1.3.6.1.2.1.1.3.0"), 1984),
            ],
        )
        assert not localhost_netsnmpy_receiver.trap_received(trap)

    async def test_when_trap_contains_unknown_variable_it_should_not_crash(self, localhost_netsnmpy_receiver):
        source = ipaddress.ip_address("127.0.0.1")
        trap = SNMPTrap(
            source=source,
            agent=source,
            generic_type=None,
            trap_oid=OID(".1.3.6.1.4.1.2636.5.1.1.1.0.2"),
            uptime=1984,
            community="public",
            version="2c",
            variables=[
                SNMPVariable(NS_OID(".1.3.6.1.2.1.1.3.0"), 1984),
                SNMPVariable(NS_OID(".1.1.1.1.1.1.1.1.1"), 42),
            ],
        )
        assert not localhost_netsnmpy_receiver.trap_received(trap)


@pytest.mark.skipif(not shutil.which("snmptrap"), reason="Cannot find snmptrap command line program")
class TestTrapReceiverExternally:
    async def test_when_trap_is_from_unknown_device_it_should_ignore_it(self, event_loop, unused_udp_port, caplog):
        receiver = TrapReceiver(address="127.0.0.1", port=unused_udp_port, loop=event_loop)
        receiver.add_community("public")
        try:
            await receiver.open()

            with caplog.at_level(logging.DEBUG):
                await send_trap_externally(OID_COLD_START, OID_SYSNAME_0, "s", "'MockDevice'", port=unused_udp_port)
                assert "ignored trap from 127.0.0.1" in caplog.text
        finally:
            receiver.close()

    async def test_when_trap_is_from_known_device_it_should_log_it(self, localhost_netsnmpy_receiver, caplog):
        with caplog.at_level(logging.DEBUG):
            await send_trap_externally(
                OID_COLD_START, OID_SYSNAME_0, "s", "'MockDevice'", port=localhost_netsnmpy_receiver.port
            )
            assert "Trap from localhost" in caplog.text
            assert OID_COLD_START in caplog.text

    async def test_when_observer_is_added_and_trap_matches_it_should_call_it(self, localhost_netsnmpy_receiver):
        observer = Mock()
        localhost_netsnmpy_receiver.observe(observer, ("SNMPv2-MIB", "coldStart"))
        await send_trap_externally(
            OID_COLD_START, OID_SYSNAME_0, "s", "'MockDevice'", port=localhost_netsnmpy_receiver.port
        )
        assert observer.handle_trap.called

    async def test_when_observer_raises_unhandled_exception_it_should_log_it(self, localhost_netsnmpy_receiver, caplog):
        crashing_observer = Mock()
        crashing_observer.handle_trap.side_effect = ValueError("mocked exception")
        localhost_netsnmpy_receiver.observe(crashing_observer, ("SNMPv2-MIB", "coldStart"))

        with caplog.at_level(logging.INFO):
            await send_trap_externally(
                OID_COLD_START, OID_SYSNAME_0, "s", "'MockDevice'", port=localhost_netsnmpy_receiver.port
            )
            assert "ValueError" in caplog.text
            assert "mocked exception" in caplog.text

    async def test_when_early_observer_returns_false_it_should_not_call_later_observers(
        self, localhost_netsnmpy_receiver, event_loop
    ):
        early_observer = Mock()
        false_result = event_loop.create_future()
        false_result.set_result(False)
        early_observer.handle_trap.return_value = false_result
        late_observer = Mock()
        localhost_netsnmpy_receiver.observe(early_observer, ("BGP4-MIB", "bgpBackwardTransition"))
        localhost_netsnmpy_receiver.observe(late_observer, ("BGP4-MIB", "bgpBackwardTransition"))
        bgp_backward_transition_trap = [
            ".1.3.6.1.2.1.15.7.2",
            ".1.3.6.1.2.1.15.3.1.7",
            "a",
            "192.168.42.42",
            ".1.3.6.1.2.1.15.3.1.14",
            "x",
            "4242",
            ".1.3.6.1.2.1.15.3.1.2",
            "i",
            "2",
        ]
        await send_trap_externally(*bgp_backward_transition_trap, port=localhost_netsnmpy_receiver.port)
        assert early_observer.handle_trap.called
        assert not late_observer.handle_trap.called

    async def test_when_trap_verification_fails_it_should_not_dispatch_trap(self, localhost_netsnmpy_receiver):
        with patch.object(localhost_netsnmpy_receiver, "_verify_trap", return_value=False):
            with patch.object(localhost_netsnmpy_receiver, "dispatch_trap") as mock_dispatch:
                await send_trap_externally(
                    OID_COLD_START, OID_SYSNAME_0, "s", "'MockDevice'", port=localhost_netsnmpy_receiver.port
                )
                assert not mock_dispatch.called
