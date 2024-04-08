from datetime import timedelta
from unittest.mock import Mock

import pytest

from zino.api.notify import Notification, Zino1NotificationProtocol
from zino.api.server import ZinoServer
from zino.state import ZinoState
from zino.statemodels import EventState, ReachabilityEvent
from zino.time import now


class TestZino1NotificationProtocol:
    def test_init_should_succeed(self):
        assert Zino1NotificationProtocol()

    def test_when_not_connected_then_peer_name_should_be_none(self):
        protocol = Zino1NotificationProtocol()
        assert protocol.peer_name is None

    def test_when_connected_then_peer_name_should_be_available(self):
        expected = "foobar"
        protocol = Zino1NotificationProtocol()
        fake_transport = Mock()
        fake_transport.get_extra_info.return_value = expected
        protocol.connection_made(fake_transport)

        assert protocol.peer_name == expected

    def test_when_connected_it_should_register_instance_in_server(self, event_loop):
        server = ZinoServer(loop=event_loop, state=ZinoState())
        protocol = Zino1NotificationProtocol(server=server)
        fake_transport = Mock()
        protocol.connection_made(fake_transport)

        assert protocol.nonce in server.notification_channels
        assert server.notification_channels[protocol.nonce] is protocol

    def test_when_disconnected_it_should_deregister_instance_from_server(self, event_loop):
        server = ZinoServer(loop=event_loop, state=ZinoState())
        protocol = Zino1NotificationProtocol(server=server)
        fake_transport = Mock()
        protocol.connection_made(fake_transport)
        protocol.connection_lost(exc=None)

        assert protocol.nonce not in server.notification_channels

    def test_notify_should_output_text_line(self):
        protocol = Zino1NotificationProtocol()
        fake_transport = Mock()
        protocol.connection_made(fake_transport)
        protocol.notify(Notification(42, "test", "data"))
        assert fake_transport.write.called
        response = fake_transport.write.call_args[0][0]
        assert response.startswith(b"42 test data")

    def test_tied_to_should_be_settable_and_gettable(self, event_loop):
        server = ZinoServer(loop=event_loop, state=ZinoState())
        protocol = Zino1NotificationProtocol()

        protocol.tied_to = server
        assert protocol.tied_to == server

    def test_goodbye_should_close_transport(self, event_loop):
        server = ZinoServer(loop=event_loop, state=ZinoState())
        protocol = Zino1NotificationProtocol(server=server)
        fake_transport = Mock()
        protocol.connection_made(fake_transport)
        protocol.goodbye()
        assert fake_transport.close.called


class TestZino1NotificationProtocolBuildNotifications:
    def test_should_make_notifications_for_regular_changed_attrs(self, fake_event):
        protocol = Zino1NotificationProtocol()
        protocol._state.events.events[fake_event.id] = fake_event
        event_copy = fake_event.model_copy(deep=True)
        event_copy.updated = now() + timedelta(seconds=5)

        notifications = list(
            protocol.build_notifications(state=protocol._state, new_event=event_copy, old_event=fake_event)
        )
        assert notifications == [Notification(event_id=42, change_type="attr", value="updated")]

    def test_should_make_notifications_for_log_changes(self, fake_event):
        protocol = Zino1NotificationProtocol()
        protocol._state.events.events[fake_event.id] = fake_event
        event_copy = fake_event.model_copy(deep=True)
        event_copy.add_log("foo")

        notifications = list(
            protocol.build_notifications(state=protocol._state, new_event=event_copy, old_event=fake_event)
        )
        assert Notification(event_id=42, change_type="log", value=1) in notifications

    def test_should_make_notifications_for_history_changes(self, fake_event):
        protocol = Zino1NotificationProtocol()
        protocol._state.events.events[fake_event.id] = fake_event
        event_copy = fake_event.model_copy(deep=True)
        event_copy.add_history("foo")

        notifications = list(
            protocol.build_notifications(state=protocol._state, new_event=event_copy, old_event=fake_event)
        )
        assert Notification(event_id=42, change_type="history", value=1) in notifications

    def test_should_make_notifications_for_state_changes(self, fake_event):
        protocol = Zino1NotificationProtocol()
        protocol._state.events.events[fake_event.id] = fake_event
        event_copy = fake_event.model_copy(deep=True)
        event_copy.state = EventState.IGNORED

        old, new = fake_event.state.value, event_copy.state.value
        expected = f"{old} {new}"

        notifications = list(
            protocol.build_notifications(state=protocol._state, new_event=event_copy, old_event=fake_event)
        )
        assert Notification(event_id=42, change_type="state", value=expected) in notifications


class TestZino1NotificationProtocolBuildAndSendNotifications:
    def test_should_send_notifications_only_to_tied_channels(self, event_loop, fake_event, changed_fake_event):
        server = ZinoServer(loop=event_loop, state=ZinoState())
        channel1 = Mock()
        channel2 = Mock()
        mock_api = Mock()

        channel1.tied_to = mock_api
        channel2.tied_to = None

        server.notification_channels["a"] = channel1
        server.notification_channels["b"] = channel2

        Zino1NotificationProtocol.build_and_send_notifications(
            server, new_event=changed_fake_event, old_event=fake_event
        )
        assert channel1.notify.called
        assert not channel2.notify.called


@pytest.fixture
def fake_event() -> ReachabilityEvent:
    return ReachabilityEvent(id=42, router="example-gw.example.org", state=EventState.OPEN)


@pytest.fixture
def changed_fake_event(fake_event) -> ReachabilityEvent:
    copy = fake_event.model_copy(deep=True)
    copy.add_history("this fake event has been changed")
    return copy
