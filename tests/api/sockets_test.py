import socket
from unittest.mock import Mock

from zino.api.sockets import enable_keepalive


class TestEnableKeepalive:
    def test_when_transport_has_a_socket_then_keepalive_should_be_enabled_on_it(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            transport = Mock()
            transport.get_extra_info.side_effect = {"socket": sock}.get

            enable_keepalive(transport)

            assert sock.getsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE)

    def test_when_transport_has_no_socket_then_it_should_not_raise(self):
        transport = Mock()
        transport.get_extra_info.return_value = None

        enable_keepalive(transport)
