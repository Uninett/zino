from datetime import timedelta
from unittest.mock import Mock, patch

import pytest

from zino.config.models import PollDevice
from zino.statemodels import InterfaceState, Port, PortStateEvent
from zino.time import now
from zino.trapd import TrapMessage
from zino.trapobservers.link_traps import LinkTrapObserver

from .. import trapd_test

OID_LINKDOWN = ".1.3.6.1.6.3.1.1.5.3"
OID_IFINDEX = ".1.3.6.1.2.1.2.2.1.1"
OID_IFOPERSTATUS = ".1.3.6.1.2.1.2.2.1.8"


class TestLinkTrapObserver:
    @pytest.mark.asyncio
    async def test_when_link_down_is_received_it_should_create_portstate_event(
        self, state_with_localhost_with_port, localhost_receiver
    ):
        assert not state_with_localhost_with_port.events.get(
            "localhost", 1, PortStateEvent
        ), "initial state should be empty"

        observer = LinkTrapObserver(
            state=localhost_receiver.state, polldevs=localhost_receiver.polldevs, loop=localhost_receiver.loop
        )
        localhost_receiver.observe(observer, *LinkTrapObserver.WANTED_TRAPS)
        await trapd_test.send_trap_externally(OID_LINKDOWN, OID_IFINDEX, "i", "1", OID_IFOPERSTATUS, "i", "2")

        assert state_with_localhost_with_port.events.get(
            "localhost", 1, PortStateEvent
        ), "no portstate event was created"

    @pytest.mark.asyncio
    async def test_when_port_does_not_match_watch_pattern_it_should_ignore_link_traps(
        self, state_with_localhost_with_port, localhost_receiver
    ):
        assert not state_with_localhost_with_port.events.get(
            "localhost", 1, PortStateEvent
        ), "initial state should be empty"
        localhost_config = PollDevice(name="localhost", address="127.0.0.1", watchpat="foo.*")
        localhost_receiver.polldevs["localhost"] = localhost_config

        observer = LinkTrapObserver(
            state=localhost_receiver.state, polldevs=localhost_receiver.polldevs, loop=localhost_receiver.loop
        )
        localhost_receiver.observe(observer, *LinkTrapObserver.WANTED_TRAPS)
        await trapd_test.send_trap_externally(OID_LINKDOWN, OID_IFINDEX, "i", "1", OID_IFOPERSTATUS, "i", "2")

        assert not state_with_localhost_with_port.events.get(
            "localhost", 1, PortStateEvent
        ), "linkDown for non-watched port was not ignored"

    @pytest.mark.asyncio
    async def test_when_port_matches_ignore_pattern_it_should_ignore_link_traps(
        self, state_with_localhost_with_port, localhost_receiver
    ):
        assert not state_with_localhost_with_port.events.get(
            "localhost", 1, PortStateEvent
        ), "initial state should be empty"
        localhost_config = PollDevice(name="localhost", address="127.0.0.1", ignorepat=".*eth0.*")
        localhost_receiver.polldevs["localhost"] = localhost_config

        observer = LinkTrapObserver(
            state=localhost_receiver.state, polldevs=localhost_receiver.polldevs, loop=localhost_receiver.loop
        )
        localhost_receiver.observe(observer, *LinkTrapObserver.WANTED_TRAPS)
        await trapd_test.send_trap_externally(OID_LINKDOWN, OID_IFINDEX, "i", "1", OID_IFOPERSTATUS, "i", "2")

        assert not state_with_localhost_with_port.events.get(
            "localhost", 1, PortStateEvent
        ), "linkDown for non-watched port was not ignored"

    def test_when_event_exists_policy_should_not_ignore_trap(self, state_with_localhost_with_port):
        observer = LinkTrapObserver(state=state_with_localhost_with_port, polldevs=Mock())
        localhost = state_with_localhost_with_port.devices.devices["localhost"]
        state_with_localhost_with_port.events.create_event(localhost.name, 1, PortStateEvent)
        assert not observer.is_port_ignored_by_policy(localhost, localhost.ports[1], is_up=False)

    def test_when_boot_time_is_unknown_policy_should_not_ignore_trap(self, state_with_localhost_with_port):
        observer = LinkTrapObserver(state=state_with_localhost_with_port, polldevs=Mock())
        localhost = state_with_localhost_with_port.devices.devices["localhost"]
        localhost.boot_time = None
        assert not observer.is_port_ignored_by_policy(localhost, localhost.ports[1], is_up=False)

    def test_when_boot_age_is_less_than_5_minutes_policy_should_ignore_trap(self, state_with_localhost_with_port):
        observer = LinkTrapObserver(state=state_with_localhost_with_port, polldevs=Mock())
        localhost = state_with_localhost_with_port.devices.devices["localhost"]
        localhost.boot_time = now() - timedelta(minutes=2)
        assert observer.is_port_ignored_by_policy(localhost, localhost.ports[1], is_up=False)

    def test_when_link_trap_is_redundant_policy_should_ignore_trap(self, state_with_localhost_with_port):
        observer = LinkTrapObserver(state=state_with_localhost_with_port, polldevs=Mock())
        localhost = state_with_localhost_with_port.devices.devices["localhost"]
        port = localhost.ports[1]
        port.state = InterfaceState.DOWN
        assert observer.is_port_ignored_by_policy(
            localhost, localhost.ports[1], is_up=False
        ), "did not ignore redundant linkDown trap"

    def test_when_link_trap_is_missing_ifindex_value_it_should_ignore_trap_early(self, state_with_localhost_with_port):
        observer = LinkTrapObserver(state=state_with_localhost_with_port, polldevs=Mock())
        trap = TrapMessage(agent=Mock())
        with patch.object(observer, "handle_link_transition") as handle_link_transition:
            assert not observer.handle_trap(trap)
            assert not handle_link_transition.called, "handle_link_transition was called"

    def test_when_link_trap_refers_to_unknown_port_it_should_ignore_trap_early(self, state_with_localhost_with_port):
        observer = LinkTrapObserver(state=state_with_localhost_with_port, polldevs=Mock())
        localhost = state_with_localhost_with_port.devices.devices["localhost"]
        trap = TrapMessage(agent=Mock(device=localhost), variables=[Mock(var="ifIndex", value=99)])
        with patch.object(observer, "handle_link_transition") as handle_link_transition:
            assert not observer.handle_trap(trap)
            assert not handle_link_transition.called, "handle_link_transition was called"


@pytest.fixture
def state_with_localhost_with_port(state_with_localhost):
    port = Port(ifindex=1, ifdescr="eth0", state=InterfaceState.UP)
    device = state_with_localhost.devices.devices["localhost"]
    device.boot_time = now() - timedelta(minutes=10)
    device.ports[port.ifindex] = port
    yield state_with_localhost
