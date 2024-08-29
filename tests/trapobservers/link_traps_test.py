import logging
from datetime import timedelta
from unittest.mock import Mock, patch

from zino import flaps
from zino.config.models import PollDevice
from zino.statemodels import FlapState, InterfaceState, PortStateEvent
from zino.time import now
from zino.trapd import TrapMessage
from zino.trapobservers.link_traps import LinkTrapObserver

from .. import trapd_test

OID_LINKDOWN = ".1.3.6.1.6.3.1.1.5.3"
OID_IFINDEX = ".1.3.6.1.2.1.2.2.1.1"
OID_IFOPERSTATUS = ".1.3.6.1.2.1.2.2.1.8"


class TestLinkTrapObserver:

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

    async def test_when_link_trap_is_missing_ifindex_value_it_should_ignore_trap_early(
        self, state_with_localhost_with_port
    ):
        observer = LinkTrapObserver(state=state_with_localhost_with_port, polldevs=Mock())
        trap = TrapMessage(agent=Mock())
        with patch.object(observer, "handle_link_transition") as handle_link_transition:
            assert not await observer.handle_trap(trap)
            assert not handle_link_transition.called, "handle_link_transition was called"

    async def test_when_link_trap_refers_to_unknown_port_it_should_ignore_trap_early(
        self, state_with_localhost_with_port
    ):
        observer = LinkTrapObserver(state=state_with_localhost_with_port, polldevs=Mock())
        localhost = state_with_localhost_with_port.devices.devices["localhost"]
        trap = TrapMessage(agent=Mock(device=localhost), variables=[Mock(var="ifIndex", value=99)])
        with patch.object(observer, "handle_link_transition") as handle_link_transition:
            assert not await observer.handle_trap(trap)
            assert not handle_link_transition.called, "handle_link_transition was called"

    async def test_should_set_lasttrans_for_new_portstate_event(
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

        event = state_with_localhost_with_port.events.get("localhost", 1, PortStateEvent)
        assert event.portstate == InterfaceState.DOWN
        assert event.lasttrans, "lasttrans not set"


class TestLinkTrapObserverHandleLinkTransitions:
    def test_when_port_is_ignored_by_patterns_it_should_not_create_portstate_event(
        self, monkeypatch, state_with_localhost_with_port
    ):
        observer = LinkTrapObserver(state=state_with_localhost_with_port, polldevs={})
        localhost = state_with_localhost_with_port.devices.devices["localhost"]
        port = next(iter(localhost.ports.values()))
        initial_count = len(state_with_localhost_with_port.events)
        monkeypatch.setattr(observer, "is_port_ignored_by_patterns", lambda *args, **kwargs: True)

        observer.handle_link_transition(localhost, port, is_up=False)

        assert len(state_with_localhost_with_port.events) == initial_count

    def test_when_port_is_ignored_by_policy_it_should_not_create_portstate_event(
        self, monkeypatch, state_with_localhost_with_port
    ):
        observer = LinkTrapObserver(state=state_with_localhost_with_port, polldevs={})
        localhost = state_with_localhost_with_port.devices.devices["localhost"]
        port = next(iter(localhost.ports.values()))
        initial_count = len(state_with_localhost_with_port.events)
        monkeypatch.setattr(observer, "is_port_ignored_by_policy", lambda *args, **kwargs: True)

        observer.handle_link_transition(localhost, port, is_up=False)

        assert len(state_with_localhost_with_port.events) == initial_count

    def test_when_link_is_down_it_should_create_portstate_event(self, state_with_localhost_with_port):
        observer = LinkTrapObserver(state=state_with_localhost_with_port, polldevs={})
        localhost = state_with_localhost_with_port.devices.devices["localhost"]
        port = next(iter(localhost.ports.values()))

        observer.handle_link_transition(localhost, port, is_up=False)

        event = state_with_localhost_with_port.events.get("localhost", port.ifindex, PortStateEvent)
        assert isinstance(event, PortStateEvent)
        assert event.router == "localhost"
        assert event.port == port.ifdescr

    def test_when_link_is_flapping_it_should_create_portstate_event_with_flapstate(
        self, state_with_localhost_with_port
    ):
        observer = LinkTrapObserver(state=state_with_localhost_with_port, polldevs={})
        localhost = state_with_localhost_with_port.devices.devices["localhost"]
        port = next(iter(localhost.ports.values()))
        flap = state_with_localhost_with_port.flapping.first_flap(("localhost", port.ifindex))
        flap.hist_val = flaps.FLAP_THRESHOLD * 2

        observer.handle_link_transition(localhost, port, is_up=False)

        event = state_with_localhost_with_port.events.get("localhost", port.ifindex, PortStateEvent)
        assert isinstance(event, PortStateEvent)
        assert event.router == "localhost"
        assert event.port == port.ifdescr
        assert event.flapstate == FlapState.FLAPPING

    def test_when_link_transitions_to_flapping_it_should_flag_active_flap_state(self, state_with_localhost_with_port):
        observer = LinkTrapObserver(state=state_with_localhost_with_port, polldevs={})
        localhost = state_with_localhost_with_port.devices.devices["localhost"]
        port = next(iter(localhost.ports.values()))
        flap = state_with_localhost_with_port.flapping.first_flap(("localhost", port.ifindex))
        flap.hist_val = flaps.FLAP_THRESHOLD * 2
        flap.in_active_flap_state = False

        observer.handle_link_transition(localhost, port, is_up=False)

        assert flap.in_active_flap_state

    def test_it_should_log_flap_stats_on_every_100_flaps(self, state_with_localhost_with_port, caplog):
        observer = LinkTrapObserver(state=state_with_localhost_with_port, polldevs={})
        localhost = state_with_localhost_with_port.devices.devices["localhost"]
        port = next(iter(localhost.ports.values()))
        flap = state_with_localhost_with_port.flapping.first_flap(("localhost", port.ifindex))
        flap.hist_val = flaps.FLAP_THRESHOLD * 2
        flap.in_active_flap_state = True
        flap.flaps = 99

        with caplog.at_level(logging.INFO):
            observer.handle_link_transition(localhost, port, is_up=False)

        assert "flaps, penalty" in caplog.text

    def test_when_link_transitions_to_non_flapping_it_should_set_event_flapstate_to_stable(
        self, state_with_localhost_with_port
    ):
        observer = LinkTrapObserver(state=state_with_localhost_with_port, polldevs={})
        localhost = state_with_localhost_with_port.devices.devices["localhost"]
        port = next(iter(localhost.ports.values()))
        index = ("localhost", port.ifindex)
        flap = state_with_localhost_with_port.flapping.first_flap(index)
        flap.hist_val = flaps.FLAP_MIN - 1
        flap.in_active_flap_state = True

        orig_event = state_with_localhost_with_port.events.get_or_create_event(
            "localhost", port.ifindex, PortStateEvent
        )
        orig_event.ifindex = port.ifindex
        orig_event.flapstate = FlapState.FLAPPING
        state_with_localhost_with_port.events.commit(orig_event)

        observer.handle_link_transition(localhost, port, is_up=True)

        event = state_with_localhost_with_port.events.get("localhost", port.ifindex, PortStateEvent)
        assert event.flapstate == FlapState.STABLE

    def test_when_link_transitions_to_non_flapping_it_should_remove_flap_state(self, state_with_localhost_with_port):
        observer = LinkTrapObserver(state=state_with_localhost_with_port, polldevs={})
        localhost = state_with_localhost_with_port.devices.devices["localhost"]
        port = next(iter(localhost.ports.values()))
        index = ("localhost", port.ifindex)
        flap = state_with_localhost_with_port.flapping.first_flap(index)
        flap.hist_val = flaps.FLAP_MIN - 1
        flap.in_active_flap_state = True

        orig_event = state_with_localhost_with_port.events.get_or_create_event(
            "localhost", port.ifindex, PortStateEvent
        )
        orig_event.ifindex = port.ifindex
        orig_event.flapstate = FlapState.FLAPPING
        state_with_localhost_with_port.events.commit(orig_event)

        observer.handle_link_transition(localhost, port, is_up=True)

        assert index not in state_with_localhost_with_port.flapping.interfaces

    def test_when_link_transitions_from_up_to_flapping_lasttrans_for_related_event_should_be_updated(
        self, state_with_localhost_with_port
    ):
        observer = LinkTrapObserver(state=state_with_localhost_with_port, polldevs={})
        localhost = state_with_localhost_with_port.devices.devices["localhost"]
        port = next(iter(localhost.ports.values()))
        flap = state_with_localhost_with_port.flapping.first_flap(("localhost", port.ifindex))
        flap.hist_val = flaps.FLAP_THRESHOLD * 2

        initial_lasttrans = now() - timedelta(minutes=5)
        events = state_with_localhost_with_port.events
        event = events.create_event("localhost", port.ifindex, PortStateEvent)
        event.ifindex = port.ifindex
        event.portstate = InterfaceState.UP
        event.lasttrans = initial_lasttrans
        events.commit(event)

        observer.handle_link_transition(localhost, port, is_up=False)

        updated_event = events[event.id]

        assert updated_event.flapstate == FlapState.FLAPPING
        assert updated_event.portstate == InterfaceState.DOWN
        assert updated_event.lasttrans > initial_lasttrans

    async def test_when_link_transitions_from_flapping_to_up_lasttrans_for_related_event_should_be_updated(
        self, state_with_localhost_with_port
    ):
        observer = LinkTrapObserver(state=state_with_localhost_with_port, polldevs={})
        localhost = state_with_localhost_with_port.devices.devices["localhost"]
        port = next(iter(localhost.ports.values()))
        index = ("localhost", port.ifindex)
        flap = state_with_localhost_with_port.flapping.first_flap(index)
        flap.hist_val = flaps.FLAP_MIN - 1
        flap.in_active_flap_state = True

        initial_lasttrans = now() - timedelta(minutes=5)
        events = state_with_localhost_with_port.events
        event = events.create_event("localhost", port.ifindex, PortStateEvent)
        event.ifindex = port.ifindex
        event.flapstate = FlapState.FLAPPING
        event.portstate = InterfaceState.DOWN
        event.lasttrans = initial_lasttrans
        events.commit(event)

        observer.handle_link_transition(localhost, port, is_up=True)

        updated_event = events[event.id]
        assert updated_event.flapstate == FlapState.STABLE
        assert updated_event.portstate == InterfaceState.UP
        assert updated_event.lasttrans > initial_lasttrans

    async def test_when_link_transitions_from_flapping_to_up_ac_down_for_related_event_should_be_updated(
        self, state_with_localhost_with_port
    ):
        observer = LinkTrapObserver(state=state_with_localhost_with_port, polldevs={})
        localhost = state_with_localhost_with_port.devices.devices["localhost"]
        port = next(iter(localhost.ports.values()))
        index = ("localhost", port.ifindex)
        flap = state_with_localhost_with_port.flapping.first_flap(index)
        flap.hist_val = flaps.FLAP_MIN - 1
        flap.in_active_flap_state = True

        initial_lasttrans = now() - timedelta(minutes=5)
        initial_ac_down = timedelta(0)
        events = state_with_localhost_with_port.events
        event = events.create_event("localhost", port.ifindex, PortStateEvent)
        event.ifindex = port.ifindex
        event.flapstate = FlapState.FLAPPING
        event.portstate = InterfaceState.DOWN
        event.ac_down = initial_ac_down
        event.lasttrans = initial_lasttrans
        events.commit(event)

        observer.handle_link_transition(localhost, port, is_up=True)

        updated_event = events[event.id]
        assert updated_event.flapstate == FlapState.STABLE
        assert updated_event.portstate == InterfaceState.UP
        assert updated_event.ac_down > initial_ac_down
