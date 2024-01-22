from unittest.mock import Mock

from zino.api.notify import Notification, Zino1NotificationProtocol
from zino.api.server import ZinoServer
from zino.state import ZinoState


class TestZino1NotificationProtocol:
    def test_init_should_succeed(self):
        assert Zino1NotificationProtocol()

    def test_when_unconnected_then_peer_name_should_be_none(self):
        protocol = Zino1NotificationProtocol()
        assert not protocol.peer_name

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
