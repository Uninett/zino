from io import BytesIO
from unittest.mock import Mock, patch

import pytest

from zino import version
from zino.api.legacy import (
    Zino1BaseServerProtocol,
    Zino1ServerProtocol,
    ZinoTestProtocol,
    requires_authentication,
)
from zino.state import ZinoState
from zino.statemodels import ReachabilityEvent


class TestZino1BaseServerProtocol:
    def test_should_init_without_error(self):
        assert Zino1BaseServerProtocol()

    def test_when_unconnected_then_peer_name_should_be_none(self):
        protocol = Zino1BaseServerProtocol()
        assert not protocol.peer_name

    def test_when_connected_then_peer_name_should_be_available(self):
        expected = "foobar"
        protocol = Zino1BaseServerProtocol()
        fake_transport = Mock()
        fake_transport.get_extra_info.return_value = expected
        protocol.connection_made(fake_transport)

        assert protocol.peer_name == expected

    def test_when_just_created_then_authenticated_should_be_false(self):
        protocol = Zino1BaseServerProtocol()
        assert not protocol.is_authenticated

    def test_when_connected_then_greeting_should_be_written(self):
        protocol = Zino1BaseServerProtocol()
        fake_transport = Mock()
        protocol.connection_made(fake_transport)
        assert fake_transport.write.called
        assert fake_transport.write.call_args[0][0].startswith(b"200 ")

    @pytest.mark.asyncio
    async def test_when_simple_data_line_is_received_then_command_should_be_dispatched(self):
        args = []

        class TestProtocol(Zino1BaseServerProtocol):
            async def do_foo(self, one, two):
                args.extend((one, two))

        protocol = TestProtocol()
        fake_transport = Mock()
        protocol.connection_made(fake_transport)
        await protocol.data_received(b"FOO bar eggs\r\n")

        assert args == ["bar", "eggs"], "do_foo() was apparently not called"

    @patch("zino.api.legacy.Zino1BaseServerProtocol._dispatch_command")
    def test_when_empty_line_is_received_then_it_should_be_ignored(self, mocked):
        protocol = Zino1BaseServerProtocol()
        fake_transport = Mock()
        protocol.connection_made(fake_transport)
        protocol.data_received(b"\r\n")

        assert not mocked.called

    def test_when_garbage_data_is_received_then_transport_should_be_closed(self):
        protocol = Zino1BaseServerProtocol()
        fake_transport = Mock()
        protocol.connection_made(fake_transport)
        protocol.data_received(b"\xff\xf4\xff\xfd\x06\r\n")

        assert fake_transport.close.called

    @pytest.mark.asyncio
    async def test_read_multiline_should_return_data_as_future(self):
        protocol = Zino1BaseServerProtocol()
        fake_transport = Mock()
        protocol.connection_made(fake_transport)
        future = protocol._read_multiline()
        protocol.data_received(b"line one\r\n")
        protocol.data_received(b"line two\r\n")
        protocol.data_received(b".\r\n")
        data = await future

        assert data == ["line one", "line two"]

    def test_when_command_is_unknown_then_dispatcher_should_respond_with_error(self):
        protocol = Zino1BaseServerProtocol()
        fake_transport = Mock()
        protocol.connection_made(fake_transport)
        protocol.data_received(b"FOO bar baz\r\n")
        assert fake_transport.write.called
        assert fake_transport.write.call_args[0][0].startswith(b"500 ")

    def test_when_privileged_command_is_requested_by_unauthenticated_client_then_dispatcher_should_respond_with_error(
        self,
    ):
        class TestProtocol(Zino1BaseServerProtocol):
            @requires_authentication
            def do_foo(self):
                pass

        protocol = TestProtocol()
        fake_transport = Mock()
        protocol.connection_made(fake_transport)
        protocol.data_received(b"FOO\r\n")

        assert fake_transport.write.called
        assert fake_transport.write.call_args[0][0].startswith(b"500 ")

    @pytest.mark.asyncio
    async def test_when_privileged_command_is_requested_by_authenticated_client_then_response_should_be_ok(self):
        class TestProtocol(Zino1BaseServerProtocol):
            @requires_authentication
            async def do_foo(self):
                self._respond_ok("foo")

        protocol = TestProtocol()
        fake_transport = Mock()
        protocol.connection_made(fake_transport)
        protocol._authenticated = True  # Fake authentication
        fake_transport.write = Mock()
        await protocol.data_received(b"FOO\r\n")

        assert fake_transport.write.called
        assert fake_transport.write.call_args[0][0].startswith(b"200 foo")

    def test_get_all_responders_should_return_mapping_of_all_commands(self):
        class TestProtocol(Zino1BaseServerProtocol):
            def do_foo(self):
                pass

        protocol = TestProtocol()
        result = protocol._get_all_responders()
        assert len(result) == 1
        assert "FOO" in result
        assert callable(result["FOO"])

    def test_when_command_has_incorrect_number_of_args_then_an_error_response_should_be_sent(self):
        class TestProtocol(Zino1BaseServerProtocol):
            async def do_foo(self, arg1, arg2):
                pass

        protocol = TestProtocol()
        fake_transport = Mock()
        protocol.connection_made(fake_transport)
        protocol.data_received(b"FOO bar\r\n")
        assert fake_transport.write.called
        response = fake_transport.write.call_args[0][0]
        assert response.startswith(b"500 ")
        assert b"arg1" in response, "arguments are not mentioned in response"
        assert b"arg2" in response, "arguments are not mentioned in response"

    def test_when_command_is_not_alphanumeric_then_get_responder_should_ignore_it(self):
        protocol = Zino1BaseServerProtocol()
        assert protocol._get_responder("-340-405??#$") is None

    @pytest.mark.asyncio
    async def test_when_command_raises_unhandled_exception_then_error_response_should_be_sent(
        self, buffered_fake_transport
    ):
        protocol = ZinoTestProtocol()
        protocol.connection_made(buffered_fake_transport)

        await protocol.data_received(b"RAISEERROR\r\n")
        assert b"500 internal error" in buffered_fake_transport.data_buffer.getvalue()

    @pytest.mark.asyncio
    async def test_when_command_raises_unhandled_exception_then_exception_should_be_logged(
        self, buffered_fake_transport, caplog
    ):
        protocol = ZinoTestProtocol()
        protocol.connection_made(buffered_fake_transport)

        await protocol.data_received(b"RAISEERROR\r\n")
        assert "ZeroDivisionError" in caplog.text


class TestZino1ServerProtocolUserCommand:
    @pytest.mark.asyncio
    async def test_when_correct_authentication_is_given_then_response_should_be_ok(self, secrets_file):
        protocol = Zino1ServerProtocol(secrets_file=secrets_file)
        fake_transport = Mock()
        protocol.connection_made(fake_transport)
        fake_transport.write = Mock()  # reset output after welcome banner
        protocol._authentication_challenge = "foo"  # fake a known challenge string
        await protocol.data_received(b"USER user1 7982ef54a5495225c5d6395c42308c074491407c\r\n")

        assert fake_transport.write.called
        response = fake_transport.write.call_args[0][0]
        assert response.startswith(b"200 ")
        assert protocol.is_authenticated

    @pytest.mark.asyncio
    async def test_when_incorrect_authentication_is_given_then_response_should_be_error(self, secrets_file):
        protocol = Zino1ServerProtocol(secrets_file=secrets_file)
        fake_transport = Mock()
        protocol.connection_made(fake_transport)
        fake_transport.write = Mock()  # reset output after welcome banner
        await protocol.data_received(b"USER user1 aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\r\n")

        assert fake_transport.write.called
        response = fake_transport.write.call_args[0][0]
        assert response.startswith(b"500")
        assert not protocol.is_authenticated

    @pytest.mark.asyncio
    async def test_when_authentication_is_attempted_more_than_once_then_response_should_be_error(self, secrets_file):
        protocol = Zino1ServerProtocol(secrets_file=secrets_file)
        fake_transport = Mock()
        protocol.connection_made(fake_transport)
        protocol._authentication_challenge = "foo"  # fake a known challenge string

        await protocol.data_received(b"USER user1 7982ef54a5495225c5d6395c42308c074491407c\r\n")
        assert protocol.is_authenticated

        fake_transport.write = Mock()  # reset output after welcome banner
        await protocol.data_received(b"USER another bar\r\n")
        assert fake_transport.write.called
        response = fake_transport.write.call_args[0][0]
        assert response.startswith(b"500")


class TestZino1ServerProtocolQuitCommand:
    @pytest.mark.asyncio
    async def test_when_quit_is_issued_then_transport_should_be_closed(self):
        protocol = Zino1ServerProtocol()
        fake_transport = Mock()
        protocol.connection_made(fake_transport)
        await protocol.data_received(b"QUIT\r\n")
        assert fake_transport.close.called


class TestZino1ServerProtocolHelpCommand:
    @pytest.mark.asyncio
    async def test_when_unauthenticated_help_is_issued_then_unauthenticated_commands_should_be_listed(
        self, buffered_fake_transport
    ):
        protocol = Zino1ServerProtocol()
        protocol.connection_made(buffered_fake_transport)

        await protocol.data_received(b"HELP\r\n")

        all_unauthenticated_command_names = set(
            name
            for name, func in protocol._get_all_responders().items()
            if not getattr(func, "requires_authentication", False)
        )
        for command_name in all_unauthenticated_command_names:
            assert (
                command_name.encode() in buffered_fake_transport.data_buffer.getvalue()
            ), f"{command_name} is not listed in HELP"

    @pytest.mark.asyncio
    async def test_when_authenticated_help_is_issued_then_all_commands_should_be_listed(self, buffered_fake_transport):
        protocol = Zino1ServerProtocol()
        protocol.connection_made(buffered_fake_transport)
        protocol._authenticated = True  # fake authentication

        await protocol.data_received(b"HELP\r\n")

        all_command_names = set(protocol._get_all_responders())
        for command_name in all_command_names:
            assert (
                command_name.encode() in buffered_fake_transport.data_buffer.getvalue()
            ), f"{command_name} is not listed in HELP"


class TestZino1ServerProtocolCaseidsCommand:
    @pytest.mark.asyncio
    async def test_should_output_a_list_of_known_event_ids(self, buffered_fake_transport):
        state = ZinoState()
        event1 = state.events.create_event("foo", None, ReachabilityEvent)
        event2 = state.events.create_event("bar", None, ReachabilityEvent)

        protocol = Zino1ServerProtocol(state=state)
        protocol.connection_made(buffered_fake_transport)
        protocol._authenticated = True  # fake authentication

        await protocol.data_received(b"CASEIDS\r\n")

        output = buffered_fake_transport.data_buffer.getvalue()
        assert f"{event1.id}\r\n".encode() in output
        assert f"{event2.id}\r\n".encode() in output


class TestZino1ServerProtocolVersionCommand:
    @pytest.mark.asyncio
    async def test_should_output_current_version(self, buffered_fake_transport):
        protocol = Zino1ServerProtocol()
        protocol.connection_made(buffered_fake_transport)
        protocol._authenticated = True  # fake authentication

        await protocol.data_received(b"VERSION\r\n")

        expected = str(version.__version__).encode()
        assert expected in buffered_fake_transport.data_buffer.getvalue()


class TestZino1TestProtocol:
    @pytest.mark.asyncio
    async def test_when_authenticated_then_authtest_should_respond_with_ok(self):
        protocol = ZinoTestProtocol()
        fake_transport = Mock()
        protocol.connection_made(fake_transport)
        protocol._authenticated = True  # Fake authentication
        fake_transport.write = Mock()
        await protocol.data_received(b"AUTHTEST\r\n")

        assert fake_transport.write.called
        assert fake_transport.write.call_args[0][0].startswith(b"200 ")

    @pytest.mark.asyncio
    async def test_multitest_should_accept_multiline_input(self, buffered_fake_transport, event_loop):
        class MockProtocol(ZinoTestProtocol):
            def _read_multiline(self):
                future = event_loop.create_future()
                future.set_result(["one", "two"])
                return future

        protocol = MockProtocol()
        protocol.connection_made(buffered_fake_transport)

        await protocol.do_multitest()
        assert b"302 " in buffered_fake_transport.data_buffer.getvalue()
        assert b"200 ok" in buffered_fake_transport.data_buffer.getvalue()


def test_requires_authentication_should_set_function_attribute():
    @requires_authentication
    def throwaway():
        pass

    assert throwaway.requires_authentication


@pytest.fixture
def buffered_fake_transport():
    """Returns a mocked Transport object in which all written output is stored in a data_buffer attribute"""
    fake_transport = Mock()
    fake_transport.data_buffer = BytesIO()

    def write_data(x: bytes):
        fake_transport.data_buffer.write(x)

    fake_transport.write = write_data
    yield fake_transport
