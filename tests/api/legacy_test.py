import re
from datetime import timedelta
from io import BytesIO
from ipaddress import IPv4Address
from unittest.mock import Mock, patch

import pytest

from zino import version
from zino.api.auth import get_challenge
from zino.api.legacy import (
    Zino1BaseServerProtocol,
    Zino1ServerProtocol,
    ZinoTestProtocol,
    requires_authentication,
)
from zino.api.server import ZinoServer
from zino.config.models import PollDevice
from zino.state import ZinoState
from zino.statemodels import (
    BGPEvent,
    BGPOperState,
    DeviceState,
    Event,
    EventState,
    FlapState,
    InterfaceState,
    MatchType,
    PmType,
    Port,
    PortStateEvent,
    ReachabilityEvent,
)
from zino.time import now


class TestZino1BaseServerProtocol:
    def test_should_init_without_error(self):
        assert Zino1BaseServerProtocol()

    def test_when_not_connected_then_peer_name_should_be_none(self):
        protocol = Zino1BaseServerProtocol()
        assert protocol.peer_name is None

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

    async def test_when_simple_data_line_is_received_then_command_should_be_dispatched(self):
        args = []

        class TestProtocol(Zino1BaseServerProtocol):
            async def do_foo(self, one, two):
                args.extend((one, two))

        protocol = TestProtocol()
        fake_transport = Mock()
        protocol.connection_made(fake_transport)
        await protocol.message_received("FOO bar eggs")

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

    @pytest.mark.timeout(5)
    async def test_data_received_should_break_down_multiline_input_packets_with_cr_and_lf(self):
        protocol = Zino1BaseServerProtocol()
        fake_transport = Mock()
        protocol.connection_made(fake_transport)
        future = protocol._read_multiline()
        protocol.data_received(b"line one\r\nline two\r\n.\r\n")
        data = await future

        assert data == ["line one", "line two"]

    @pytest.mark.timeout(5)
    async def test_data_received_should_break_down_multiline_input_packets_with_just_lf(self):
        protocol = Zino1BaseServerProtocol()
        fake_transport = Mock()
        protocol.connection_made(fake_transport)
        future = protocol._read_multiline()
        protocol.data_received(b"line one\nline two\n.\n")
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

    async def test_when_privileged_command_is_requested_by_authenticated_client_then_response_should_be_ok(self):
        class TestProtocol(Zino1BaseServerProtocol):
            @requires_authentication
            async def do_foo(self):
                self._respond_ok("foo")

        protocol = TestProtocol()
        fake_transport = Mock()
        protocol.connection_made(fake_transport)
        protocol.user = "fake"
        fake_transport.write = Mock()
        await protocol.message_received("FOO")

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
        assert callable(result["FOO"].function)

    def test_when_command_has_too_few_args_then_an_error_response_should_be_sent(self):
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

    async def test_when_command_has_too_many_args_then_it_should_ignore_the_extraneous_args(self):
        class TestProtocol(Zino1BaseServerProtocol):
            async def do_foo(self, arg1, arg2):
                self._respond_ok()

        protocol = TestProtocol()
        fake_transport = Mock()
        protocol.connection_made(fake_transport)
        await protocol.message_received("FOO bar baz qux")
        assert fake_transport.write.called
        response = fake_transport.write.call_args[0][0]
        assert response.startswith(b"200 ")

    def test_when_command_is_not_alphanumeric_then_get_responder_should_ignore_it(self):
        protocol = Zino1BaseServerProtocol()
        responder, args = protocol._get_responder("-340-405??#$")
        assert responder is None

    def test_when_multiple_responders_match_then_get_responder_should_return_the_longest_name_match(self):
        class TestProtocol(Zino1BaseServerProtocol):
            async def do_foo(self):
                pass

            async def do_foo_bar(self):
                pass

        protocol = TestProtocol()
        responder, args = protocol._get_responder("FOO BAR")
        assert responder.name == "FOO BAR"

    async def test_when_command_raises_unhandled_exception_then_error_response_should_be_sent(
        self, buffered_fake_transport
    ):
        protocol = ZinoTestProtocol()
        protocol.connection_made(buffered_fake_transport)

        await protocol.message_received("RAISEERROR")
        assert b"500 internal error" in buffered_fake_transport.data_buffer.getvalue()

    async def test_when_command_raises_unhandled_exception_then_exception_should_be_logged(
        self, buffered_fake_transport, caplog
    ):
        protocol = ZinoTestProtocol()
        protocol.connection_made(buffered_fake_transport)

        await protocol.message_received("RAISEERROR")
        assert "ZeroDivisionError" in caplog.text

    def test_when_connected_it_should_register_instance_in_server(self, event_loop):
        server = ZinoServer(loop=event_loop, state=ZinoState(), polldevs=dict())
        protocol = Zino1BaseServerProtocol(server=server)
        fake_transport = Mock()
        protocol.connection_made(fake_transport)

        assert protocol in server.active_clients

    def test_when_disconnected_it_should_deregister_instance_from_server(self, event_loop):
        server = ZinoServer(loop=event_loop, state=ZinoState(), polldevs=dict())
        protocol = Zino1BaseServerProtocol(server=server)
        fake_transport = Mock()
        protocol.connection_made(fake_transport)
        protocol.connection_lost(exc=None)

        assert protocol not in server.active_clients


class TestZino1ServerProtocolTranslateCaseIdToEvent:
    async def test_when_caseid_exists_it_should_return_event_object(self):
        args = []

        class TestProtocol(Zino1ServerProtocol):
            @Zino1ServerProtocol._translate_case_id_to_event
            async def do_foo(self, event: Event):
                args.append(event)
                self._respond_ok()

        protocol = TestProtocol()

        test_event = protocol._state.events.create_event("example-gw", None, ReachabilityEvent)
        protocol._state.events.commit(test_event)

        fake_transport = Mock()
        protocol.connection_made(fake_transport)
        await protocol.do_foo(test_event.id)

        assert args[0] is test_event

    async def test_when_caseid_doesnt_exist_the_return_value_should_be_awaitable(self):
        class TestProtocol(Zino1ServerProtocol):
            @Zino1ServerProtocol._translate_case_id_to_event
            async def do_foo(self, event: Event):
                self._respond_ok()
                return "foo"

        protocol = TestProtocol()
        fake_transport = Mock()
        protocol.connection_made(fake_transport)
        result = await protocol.do_foo(42)
        assert not result


class TestZino1ServerProtocolUserCommand:
    async def test_when_correct_authentication_is_given_then_response_should_be_ok(self, secrets_file):
        protocol = Zino1ServerProtocol(secrets_file=secrets_file)
        fake_transport = Mock()
        protocol.connection_made(fake_transport)
        fake_transport.write = Mock()  # reset output after welcome banner
        protocol._authentication_challenge = "foo"  # fake a known challenge string
        await protocol.message_received("USER user1 7982ef54a5495225c5d6395c42308c074491407c")

        assert fake_transport.write.called
        response = fake_transport.write.call_args[0][0]
        assert response.startswith(b"200 ")
        assert protocol.is_authenticated

    async def test_when_incorrect_authentication_is_given_then_response_should_be_error(self, secrets_file):
        protocol = Zino1ServerProtocol(secrets_file=secrets_file)
        fake_transport = Mock()
        protocol.connection_made(fake_transport)
        fake_transport.write = Mock()  # reset output after welcome banner
        await protocol.message_received("USER user1 aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")

        assert fake_transport.write.called
        response = fake_transport.write.call_args[0][0]
        assert response.startswith(b"500")
        assert not protocol.is_authenticated

    async def test_when_authentication_is_attempted_more_than_once_then_response_should_be_error(self, secrets_file):
        protocol = Zino1ServerProtocol(secrets_file=secrets_file)
        fake_transport = Mock()
        protocol.connection_made(fake_transport)
        protocol._authentication_challenge = "foo"  # fake a known challenge string

        await protocol.message_received("USER user1 7982ef54a5495225c5d6395c42308c074491407c")
        assert protocol.is_authenticated

        fake_transport.write = Mock()  # reset output after welcome banner
        await protocol.message_received("USER another bar")
        assert fake_transport.write.called
        response = fake_transport.write.call_args[0][0]
        assert response.startswith(b"500")


class TestZino1ServerProtocolQuitCommand:
    async def test_when_quit_is_issued_then_transport_should_be_closed(self, authenticated_protocol):
        await authenticated_protocol.message_received("QUIT")
        assert authenticated_protocol.transport.close.called


class TestZino1ServerProtocolHelpCommand:
    async def test_when_unauthenticated_help_is_issued_then_unauthenticated_top_level_commands_should_be_listed(
        self, buffered_fake_transport
    ):
        protocol = Zino1ServerProtocol()
        protocol.connection_made(buffered_fake_transport)

        await protocol.message_received("HELP")

        all_unauthenticated_command_names = set(
            name
            for name, responder in protocol._get_top_level_responders().items()
            if not getattr(responder.function, "requires_authentication", False)
        )
        for command_name in all_unauthenticated_command_names:
            assert command_name.encode() in buffered_fake_transport.data_buffer.getvalue(), (
                f"{command_name} is not listed in HELP"
            )

    async def test_when_authenticated_help_is_issued_then_all_top_level_commands_should_be_listed(
        self, authenticated_protocol
    ):
        await authenticated_protocol.message_received("HELP")

        all_command_names = set(authenticated_protocol._get_top_level_responders())
        for command_name in all_command_names:
            assert command_name.encode() in authenticated_protocol.transport.data_buffer.getvalue(), (
                f"{command_name} is not listed in HELP"
            )


class TestZino1ServerProtocolCaseidsCommand:
    async def test_should_output_a_list_of_known_event_ids(self, authenticated_protocol):
        state = authenticated_protocol._state
        event1 = state.events.create_event("foo", None, ReachabilityEvent)
        state.events.commit(event1)
        event2 = state.events.create_event("bar", None, ReachabilityEvent)
        state.events.commit(event2)

        await authenticated_protocol.message_received("CASEIDS")

        output = authenticated_protocol.transport.data_buffer.getvalue()
        assert f"{event1.id}\r\n".encode() in output
        assert f"{event2.id}\r\n".encode() in output

    async def test_should_output_a_list_of_only_ids_of_non_closed_events(self, authenticated_protocol):
        state = authenticated_protocol._state
        event1 = state.events.create_event("foo", None, ReachabilityEvent)
        state.events.commit(event1)
        event2 = state.events.create_event("bar", None, ReachabilityEvent)
        event2.state = EventState.CLOSED
        state.events.commit(event2)

        await authenticated_protocol.message_received("CASEIDS")

        output = authenticated_protocol.transport.data_buffer.getvalue()
        assert f"{event1.id}\r\n".encode() in output
        assert f"{event2.id}\r\n".encode() not in output


class TestZino1ServerProtocolVersionCommand:
    async def test_should_output_current_version(self, buffered_fake_transport):
        protocol = Zino1ServerProtocol()
        protocol.connection_made(buffered_fake_transport)
        protocol._authenticated = True  # fake authentication

        await protocol.message_received("VERSION")

        expected = str(version.__version__).encode()
        assert expected in buffered_fake_transport.data_buffer.getvalue()


class TestZino1ServerProtocolGetattrsCommand:
    async def test_should_output_correct_attrs(self, authenticated_protocol):
        state = authenticated_protocol._state
        event1 = state.events.create_event("foo", None, ReachabilityEvent)
        state.events.commit(event1)

        await authenticated_protocol.message_received(f"GETATTRS {event1.id}")

        output = authenticated_protocol.transport.data_buffer.getvalue().decode()
        assert f"id: {event1.id}\r\n" in output
        assert f"router: {event1.router}\r\n" in output
        assert f"state: {event1.state.value}\r\n" in output

    async def test_when_caseid_is_invalid_it_should_output_error(self, authenticated_protocol):
        await authenticated_protocol.message_received("GETATTRS 42")

        output = authenticated_protocol.transport.data_buffer.getvalue().decode()
        assert "\r\n500 " in output

    async def test_should_output_correct_attrs_for_alias(self, authenticated_protocol):
        state = authenticated_protocol._state
        event1 = state.events.create_event("foo", IPv4Address("127.0.0.1"), BGPEvent)
        event1.operational_state = BGPOperState.ESTABLISHED
        event1.remote_as = 2
        state.events.commit(event1)

        await authenticated_protocol.message_received(f"GETATTRS {event1.id}")

        output = authenticated_protocol.transport.data_buffer.getvalue().decode()
        assert f"id: {event1.id}\r\n" in output
        assert f"router: {event1.router}\r\n" in output
        assert f"state: {event1.state.value}\r\n" in output
        assert f"bgpOS: {event1.operational_state}\r\n" in output
        assert f"remote-AS: {event1.remote_as}\r\n" in output


class TestZino1ServerProtocolGethistCommand:
    async def test_should_output_all_lines(self, authenticated_protocol):
        state = authenticated_protocol._state
        event = state.events.create_event("foo", None, ReachabilityEvent)
        event.add_history("line one\nline two\nline three")
        event.add_history("another line one\nanother line two\nanother line")
        state.events.commit(event)

        await authenticated_protocol.message_received(f"GETHIST {event.id}")

        output: str = authenticated_protocol.transport.data_buffer.getvalue().decode()

        output = output[output.find("301 history follows") :]
        lines = output.splitlines()
        assert len(lines) == 9
        assert lines[-1] == "."
        assert all(line[0].isdigit() or line.startswith(" ") for line in lines[:-1])

    async def test_when_caseid_is_invalid_it_should_output_error(self, authenticated_protocol):
        await authenticated_protocol.message_received("GETHIST 999")

        output = authenticated_protocol.transport.data_buffer.getvalue().decode()
        assert "\r\n500 " in output


class TestZino1ServerProtocolGetlogCommand:
    async def test_should_output_all_lines(self, authenticated_protocol):
        state = authenticated_protocol._state
        event = state.events.create_event("foo", None, ReachabilityEvent)
        event.add_log("line one\nline two\nline three")
        event.add_log("another line one\nanother line two\nanother line")
        state.events.commit(event)

        await authenticated_protocol.message_received(f"GETLOG {event.id}")

        output: str = authenticated_protocol.transport.data_buffer.getvalue().decode()

        output = output[output.find("300 log follows") :]
        lines = output.splitlines()
        assert len(lines) == 8
        assert lines[-1] == "."
        assert all(line[0].isdigit() or line.startswith(" ") for line in lines[:-1])

    async def test_when_caseid_is_invalid_it_should_output_error(self, authenticated_protocol):
        await authenticated_protocol.message_received("GETLOG 999")

        output = authenticated_protocol.transport.data_buffer.getvalue().decode()
        assert "\r\n500 " in output


class TestZino1ServerProtocolAddhistCommand:
    async def test_should_add_history_entry_to_event(self, authenticated_protocol, event_loop):
        state = authenticated_protocol._state
        event = state.events.create_event("foo", None, ReachabilityEvent)
        state.events.commit(event)

        def mock_multiline():
            future = event_loop.create_future()
            future.set_result(["one", "two"])
            return future

        with patch.object(authenticated_protocol, "_read_multiline", mock_multiline):
            pre_count = len(event.history)
            await authenticated_protocol.do_addhist(event.id)
            committed_event = state.events[event.id]
            assert len(committed_event.history) > pre_count

    async def test_should_prefix_history_message_with_username(self, authenticated_protocol, event_loop):
        state = authenticated_protocol._state
        event = state.events.create_event("foo", None, ReachabilityEvent)
        state.events.commit(event)

        def mock_multiline():
            future = event_loop.create_future()
            future.set_result(["sapient foobar", "cromulent dingbat"])
            return future

        with patch.object(authenticated_protocol, "_read_multiline", mock_multiline):
            await authenticated_protocol.do_addhist(event.id)
            committed_event = state.events[event.id]
            entry = committed_event.history[-1]
            assert entry.message.startswith(authenticated_protocol.user)

    async def test_when_caseid_is_invalid_it_should_output_error(self, authenticated_protocol):
        await authenticated_protocol.message_received("ADDHIST 999")

        output = authenticated_protocol.transport.data_buffer.getvalue().decode()
        assert "\r\n500 " in output


class TestZino1ServerProtocolSetstateCommand:
    async def test_when_caseid_is_invalid_it_should_output_error(self, authenticated_protocol):
        await authenticated_protocol.message_received("SETSTATE 999 ignored")

        output = authenticated_protocol.transport.data_buffer.getvalue().decode()
        assert "\r\n500 " in output

    async def test_when_state_is_invalid_it_should_output_error(self, authenticated_protocol):
        state = authenticated_protocol._state
        event = state.events.create_event("foo", None, ReachabilityEvent)
        state.events.commit(event)

        await authenticated_protocol.message_received(f"SETSTATE {event.id} invalidgabbagabba")

        output = authenticated_protocol.transport.data_buffer.getvalue().decode()
        assert "\r\n500 " in output

    async def test_when_event_is_closed_it_should_output_error_and_stay_closed(self, authenticated_protocol):
        state = authenticated_protocol._state
        event = state.events.create_event("foo", None, ReachabilityEvent)
        event.state = EventState.CLOSED
        state.events.commit(event)

        await authenticated_protocol.message_received(f"SETSTATE {event.id} ignored")

        output = authenticated_protocol.transport.data_buffer.getvalue().decode()
        assert "\r\n500 " in output

        event = state.events[event.id]
        assert event.state == EventState.CLOSED

    async def test_when_caseid_and_state_is_valid_event_state_should_be_changed(self, authenticated_protocol):
        state = authenticated_protocol._state
        event = state.events.create_event("foo", None, ReachabilityEvent)
        state.events.commit(event)

        await authenticated_protocol.message_received(f"SETSTATE {event.id} ignored")

        output = authenticated_protocol.transport.data_buffer.getvalue().decode()
        assert "\r\n200 " in output

        updated_event = state.events[event.id]
        assert updated_event.state == EventState.IGNORED

    async def test_when_caseid_and_state_is_valid_event_history_should_contain_username(self, authenticated_protocol):
        state = authenticated_protocol._state
        event = state.events.create_event("foo", None, ReachabilityEvent)
        state.events.commit(event)

        await authenticated_protocol.message_received(f"SETSTATE {event.id} ignored")

        output = authenticated_protocol.transport.data_buffer.getvalue().decode()
        assert "\r\n200 " in output

        updated_event = state.events[event.id]
        last_history_entry = updated_event.history[-1]
        assert authenticated_protocol.user in last_history_entry.message


class TestZino1ServerProtocolCommunityCommand:
    async def test_should_output_community_for_router(self, authenticated_protocol):
        router_name = "buick.lab.example.org"
        community = "public"
        device = PollDevice(
            name=router_name,
            address="127.0.0.1",
            port=666,
            community=community,
        )
        polldevs = {device.name: device}
        authenticated_protocol._polldevs = polldevs

        await authenticated_protocol.message_received(f"COMMUNITY {router_name}")

        output = authenticated_protocol.transport.data_buffer.getvalue()
        assert f"201 {device.community}\r\n".encode() in output

    async def test_should_output_error_response_for_unknown_router(self, authenticated_protocol):
        await authenticated_protocol.message_received("COMMUNITY unknown.router.example.org")

        output = authenticated_protocol.transport.data_buffer.getvalue()
        assert b"500 router unknown\r\n" in output


class TestZino1ServerProtocolNtieCommand:
    async def test_when_nonce_is_bogus_it_should_respond_with_error(self, event_loop, authenticated_protocol):
        server = ZinoServer(loop=event_loop, state=ZinoState(), polldevs=dict())
        server.notification_channels = dict()  # Ensure there are none for this test
        authenticated_protocol.server = server

        await authenticated_protocol.message_received("NTIE cromulent")

        output = authenticated_protocol.transport.data_buffer.getvalue().decode()
        assert "\r\n500 " in output

    async def test_when_nonce_exists_it_should_respond_with_ok(self, event_loop, authenticated_protocol):
        server = ZinoServer(loop=event_loop, state=ZinoState(), polldevs=dict())
        nonce = get_challenge()
        mock_channel = Mock()
        server.notification_channels[nonce] = mock_channel
        authenticated_protocol.server = server

        await authenticated_protocol.message_received(f"NTIE {nonce}")

        output = authenticated_protocol.transport.data_buffer.getvalue().decode()
        assert "\r\n200 " in output

    async def test_when_nonce_exists_it_should_tie_the_corresponding_channel(self, event_loop, authenticated_protocol):
        server = ZinoServer(loop=event_loop, state=ZinoState(), polldevs=dict())
        nonce = get_challenge()
        mock_channel = Mock()
        server.notification_channels[nonce] = mock_channel
        authenticated_protocol.server = server

        await authenticated_protocol.message_received(f"NTIE {nonce}")

        assert mock_channel.tied_to is authenticated_protocol


class TestZino1ServerProtocolPollrtrCommand:
    async def test_should_add_run_all_tasks_job(self, authenticated_protocol):
        router_name = "buick.lab.example.org"
        community = "public"
        device = PollDevice(
            name=router_name,
            address="127.0.0.1",
            port=666,
            community=community,
        )
        polldevs = {device.name: device}
        authenticated_protocol._polldevs = polldevs

        with patch("zino.api.legacy.get_scheduler") as get_scheduler:
            mock_scheduler = Mock()
            get_scheduler.return_value = mock_scheduler

            await authenticated_protocol.message_received(f"POLLRTR {router_name}")

        output = authenticated_protocol.transport.data_buffer.getvalue()
        assert "200 ok\r\n".encode() in output
        assert mock_scheduler.add_job.called

    async def test_should_output_error_response_for_unknown_router(self, authenticated_protocol):
        unknown_router = "unknown.router.example.org"
        await authenticated_protocol.message_received(f"POLLRTR {unknown_router}")

        output = authenticated_protocol.transport.data_buffer.getvalue()
        assert f"500 Router {unknown_router} unknown\r\n".encode() in output


class TestZino1ServerProtocolPollintfCommand:
    async def test_should_call_poll_single_interface(self, authenticated_protocol):
        router_name = "buick.lab.example.org"
        community = "public"
        device = PollDevice(
            name=router_name,
            address="127.0.0.1",
            port=666,
            community=community,
        )
        polldevs = {device.name: device}
        authenticated_protocol._polldevs = polldevs

        with patch(
            "zino.tasks.linkstatetask.LinkStateTask.schedule_verification_of_single_port", Mock()
        ) as mock_schedule_verification:
            await authenticated_protocol.message_received(f"POLLINTF {router_name} 1")

        output = authenticated_protocol.transport.data_buffer.getvalue()
        assert "200 ok\r\n".encode() in output
        assert mock_schedule_verification.called

    async def test_should_output_error_response_for_unknown_router(self, authenticated_protocol):
        unknown_router = "unknown.router.example.org"
        await authenticated_protocol.message_received(f"POLLINTF {unknown_router} 1")

        output = authenticated_protocol.transport.data_buffer.getvalue()
        assert f"500 Router {unknown_router} unknown\r\n".encode() in output

    async def test_should_output_error_response_for_invalid_ifindex(self, authenticated_protocol):
        router_name = "buick.lab.example.org"
        community = "public"
        device = PollDevice(
            name=router_name,
            address="127.0.0.1",
            port=666,
            community=community,
        )
        polldevs = {device.name: device}
        authenticated_protocol._polldevs = polldevs
        await authenticated_protocol.message_received(f"POLLINTF {router_name} foobar")

        output = authenticated_protocol.transport.data_buffer.getvalue()
        assert "500 foobar is an invalid ifindex value".encode() in output


class TestZino1ServerProtocolClearflapCommand:
    async def test_it_should_set_event_flapstate_to_stable_and_respond_with_ok(self, authenticated_protocol):
        # Arrange bigly
        router_name = "buick.lab.example.org"
        community = "public"
        device = PollDevice(
            name=router_name,
            address="127.0.0.1",
            port=666,
            community=community,
        )
        polldevs = {device.name: device}
        authenticated_protocol._polldevs = polldevs

        device_state = DeviceState(name=router_name)
        port = Port(ifindex=1, ifdescr="eth0", ifalias="Test port", state=InterfaceState.FLAPPING)
        device_state.ports[port.ifindex] = port

        state = authenticated_protocol._state
        state.devices.devices[router_name] = device_state

        event = state.events.create_event(router_name, 1, PortStateEvent)
        event.ifindex = 1
        event.flapstate = FlapState.FLAPPING
        state.events.commit(event)

        # Act
        await authenticated_protocol.message_received(f"CLEARFLAP {router_name} 1")

        # Assert
        output = authenticated_protocol.transport.data_buffer.getvalue()
        assert "200 ".encode() in output
        updated_event = state.events.get(router_name, 1, PortStateEvent)
        assert updated_event
        assert updated_event.flapstate == FlapState.STABLE

    async def test_it_should_output_error_response_for_unknown_router(self, authenticated_protocol):
        unknown_router = "unknown.router.example.org"
        await authenticated_protocol.message_received(f"CLEARFLAP {unknown_router} 1")

        output = authenticated_protocol.transport.data_buffer.getvalue()
        assert f"500 Router {unknown_router} unknown\r\n".encode() in output

    async def test_it_should_output_error_response_for_invalid_ifindex(self, authenticated_protocol):
        router_name = "buick.lab.example.org"
        community = "public"
        device = PollDevice(
            name=router_name,
            address="127.0.0.1",
            port=666,
            community=community,
        )
        polldevs = {device.name: device}
        authenticated_protocol._polldevs = polldevs

        await authenticated_protocol.message_received(f"CLEARFLAP {router_name} foobar")

        output = authenticated_protocol.transport.data_buffer.getvalue()
        assert "500 foobar is an invalid ifindex value".encode() in output


class TestZino1TestProtocol:
    async def test_when_authenticated_then_authtest_should_respond_with_ok(self):
        protocol = ZinoTestProtocol()
        fake_transport = Mock()
        protocol.connection_made(fake_transport)
        protocol.user = "foo"
        fake_transport.write = Mock()
        await protocol.message_received("AUTHTEST")

        assert fake_transport.write.called
        assert fake_transport.write.call_args[0][0].startswith(b"200 ")

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


class TestZino1ServerProtocolPmCommand:
    async def test_it_should_always_return_a_500_error(self, authenticated_protocol):
        await authenticated_protocol.message_received("PM")

        assert b"500 " in authenticated_protocol.transport.data_buffer.getvalue()


class TestZino1ServerProtocolPmHelpCommand:
    async def test_when_authenticated_pm_help_is_issued_then_all_pm_subcommands_should_be_listed(
        self, authenticated_protocol
    ):
        await authenticated_protocol.message_received("PM HELP")

        all_command_names = set(
            responder.name.removeprefix("PM ")
            for responder in authenticated_protocol._responders.values()
            if responder.name.startswith("PM ")
        )
        for command_name in all_command_names:
            assert command_name.encode() in authenticated_protocol.transport.data_buffer.getvalue(), (
                f"{command_name} is not listed in PM HELP"
            )


class TestZino1ServerProtocolPmListCommand:
    async def test_when_authenticated_should_list_all_pm_ids(
        self, authenticated_protocol, active_device_pm, active_portstate_pm
    ):
        planned_maintenances = authenticated_protocol._state.planned_maintenances.planned_maintenances
        planned_maintenances[active_device_pm.id] = active_device_pm
        planned_maintenances[active_portstate_pm.id] = active_portstate_pm

        await authenticated_protocol.message_received("PM LIST")
        response = authenticated_protocol.transport.data_buffer.getvalue().decode("utf-8")

        assert re.search(r"\b300 \b", response), "Expected response to contain status code 300"

        assert re.search(rf"\b{active_device_pm.id}\b", response), (
            f"Expected response to contain id {active_device_pm.id}"
        )
        assert re.search(rf"\b{active_portstate_pm.id}\b", response), (
            f"Expected response to contain id {active_portstate_pm.id}"
        )


class TestZino1ServerProtocolPmCancelCommand:
    async def test_when_authenticated_should_cancel_pm(self, authenticated_protocol, active_device_pm):
        planned_maintenances = authenticated_protocol._state.planned_maintenances.planned_maintenances
        planned_maintenances[active_device_pm.id] = active_device_pm
        await authenticated_protocol.message_received(f"PM CANCEL {active_device_pm.id}")
        response = authenticated_protocol.transport.data_buffer.getvalue().decode("utf-8")

        assert re.search(r"\b200 \b", response), "Expected response to contain status code 200"

        assert active_device_pm.id not in planned_maintenances
        log_messages = [log.message for log in active_device_pm.log]
        assert f"PM closed by {authenticated_protocol.user}: PM cancelled" in log_messages

    async def test_when_authenticated_should_do_nothing_for_ended_pm(self, authenticated_protocol, ended_pm):
        planned_maintenances = authenticated_protocol._state.planned_maintenances.planned_maintenances
        await authenticated_protocol.message_received(f"PM CANCEL {ended_pm.id}")
        response = authenticated_protocol.transport.data_buffer.getvalue().decode("utf-8")

        assert re.search(r"\b200 \b", response), "Expected response to contain status code 200"

        assert ended_pm.id not in planned_maintenances
        log_messages = [log.message for log in ended_pm.log]
        assert f"PM closed by {authenticated_protocol.user}: PM cancelled" not in log_messages


class TestZino1ServerProtocolPmAddLogCommand:
    async def test_should_add_log_entry_to_pm(self, authenticated_protocol, active_device_pm, event_loop):
        planned_maintenances = authenticated_protocol._state.planned_maintenances.planned_maintenances
        planned_maintenances[active_device_pm.id] = active_device_pm

        def mock_multiline():
            future = event_loop.create_future()
            future.set_result(["one", "two"])
            return future

        with patch.object(authenticated_protocol, "_read_multiline", mock_multiline):
            await authenticated_protocol.do_pm_addlog(active_device_pm.id)

        assert any(
            authenticated_protocol.user in log.message and "one" in log.message and "two" in log.message
            for log in active_device_pm.log
        )


class TestZino1ServerProtocolPmLogCommand:
    async def test_should_output_pm_log(self, authenticated_protocol, active_device_pm):
        planned_maintenances = authenticated_protocol._state.planned_maintenances.planned_maintenances
        planned_maintenances[active_device_pm.id] = active_device_pm

        active_device_pm.add_log("line one\nline two\nline three")
        active_device_pm.add_log("another line one\nanother line two\nanother line")

        await authenticated_protocol.message_received(f"PM LOG {active_device_pm.id}")

        output: str = authenticated_protocol.transport.data_buffer.getvalue().decode()

        output = output[output.find("300 log follows") :]
        lines = output.splitlines()

        assert len(lines) == 8
        assert lines[-1] == "."
        assert all(line[0].isdigit() or line.startswith(" ") for line in lines[:-1])


class TestZino1ServerProtocolPmDetailsCommand:
    async def test_when_authenticated_should_output_device_pm_details(self, authenticated_protocol, active_device_pm):
        planned_maintenances = authenticated_protocol._state.planned_maintenances.planned_maintenances
        planned_maintenances[active_device_pm.id] = active_device_pm
        await authenticated_protocol.message_received(f"PM DETAILS {active_device_pm.id}")
        response = authenticated_protocol.transport.data_buffer.getvalue().decode("utf-8")

        assert re.search(r"\b200 \b", response), "Expected response to contain status code 200"

        assert str(int(active_device_pm.start_time.timestamp())) in response, (
            f"Expected response to contain start time {active_device_pm.start_time.timestamp()}"
        )
        assert str(int(active_device_pm.end_time.timestamp())) in response, (
            f"Expected response to contain end time {active_device_pm.end_time.timestamp()}"
        )
        assert str(active_device_pm.id) in response, f"Expected response to contain id {active_device_pm.id}"
        assert str(active_device_pm.type) in response, f"Expected response to contain type {active_device_pm.type}"
        assert str(active_device_pm.match_type) in response, (
            f"Expected response to contain match type {active_device_pm.match_type}"
        )
        assert active_device_pm.match_expression in response, (
            f"Expected response to contain match expression {active_device_pm.match_expression}"
        )

    async def test_when_authenticated_should_output_portstate_pm_details(
        self, authenticated_protocol, active_portstate_pm
    ):
        planned_maintenances = authenticated_protocol._state.planned_maintenances.planned_maintenances
        planned_maintenances[active_portstate_pm.id] = active_portstate_pm
        await authenticated_protocol.message_received(f"PM DETAILS {active_portstate_pm.id}")
        response = authenticated_protocol.transport.data_buffer.getvalue().decode("utf-8")

        assert re.search(r"\b200 \b", response), "Expected response to contain status code 200"

        assert str(int(active_portstate_pm.start_time.timestamp())) in response, (
            f"Expected response to contain start time {active_portstate_pm.start_time.timestamp()}"
        )
        assert str(int(active_portstate_pm.end_time.timestamp())) in response, (
            f"Expected response to contain end time {active_portstate_pm.end_time.timestamp()}"
        )
        assert str(active_portstate_pm.id) in response, f"Expected response to contain id {active_portstate_pm.id}"
        assert str(active_portstate_pm.type) in response, (
            f"Expected response to contain type {active_portstate_pm.type}"
        )
        assert str(active_portstate_pm.match_type) in response, (
            f"Expected response to contain match type {active_portstate_pm.match_type}"
        )
        assert str(active_portstate_pm.match_device) in response, (
            f"Expected response to contain match device {active_portstate_pm.match_device}"
        )
        assert active_portstate_pm.match_expression in response, (
            f"Expected response to contain match expression {active_portstate_pm.match_expression}"
        )


class TestZino1ServerProtocolPmAddCommand:
    async def test_when_authenticated_should_create_device_pm(self, authenticated_protocol):
        planned_maintenances = authenticated_protocol._state.planned_maintenances.planned_maintenances
        start_time = int((now() + timedelta(minutes=10)).timestamp())
        end_time = int((now() + timedelta(hours=1)).timestamp())
        pm_type = PmType.DEVICE
        match_type = MatchType.EXACT
        match_expression = "localhost"
        await authenticated_protocol.message_received(
            f"PM ADD {start_time} {end_time} {pm_type} {match_type} {match_expression}"
        )
        response = authenticated_protocol.transport.data_buffer.getvalue().decode("utf-8")

        assert re.search(r"\b200 \b", response), "Expected response to contain status code 200"
        pm_id = re.search(r"PM id (?P<pm_id>\d+) successfully added", response).group("pm_id")
        assert pm_id, "Expected response to contain PM successfully added message"
        assert planned_maintenances.get(int(pm_id), None)

    async def test_when_authenticated_should_create_portstate_pm(self, authenticated_protocol):
        planned_maintenances = authenticated_protocol._state.planned_maintenances.planned_maintenances
        start_time = int((now() + timedelta(minutes=10)).timestamp())
        end_time = int((now() + timedelta(hours=1)).timestamp())
        pm_type = PmType.PORTSTATE
        match_type = MatchType.REGEXP
        match_expression = "eth0"
        await authenticated_protocol.message_received(
            f"PM ADD {start_time} {end_time} {pm_type} {match_type} {match_expression}"
        )
        response = authenticated_protocol.transport.data_buffer.getvalue().decode("utf-8")

        assert re.search(r"\b200 \b", response), "Expected response to contain status code 200"
        pm_id = re.search(r"PM id (?P<pm_id>\d+) successfully added", response).group("pm_id")
        assert pm_id, "Expected response to contain PM successfully added message"
        assert planned_maintenances.get(int(pm_id), None)

    async def test_when_authenticated_should_create_portstate_pm_with_interface_regexp(self, authenticated_protocol):
        planned_maintenances = authenticated_protocol._state.planned_maintenances.planned_maintenances
        start_time = int((now() + timedelta(minutes=10)).timestamp())
        end_time = int((now() + timedelta(hours=1)).timestamp())
        pm_type = PmType.PORTSTATE
        match_type = MatchType.INTF_REGEXP
        match_expression = "eth0"
        match_device = "localhost"
        await authenticated_protocol.message_received(
            f"PM ADD {start_time} {end_time} {pm_type} {match_type} {match_device} {match_expression}"
        )
        response = authenticated_protocol.transport.data_buffer.getvalue().decode("utf-8")

        assert re.search(r"\b200 \b", response), "Expected response to contain status code 200"
        pm_id = re.search(r"PM id (?P<pm_id>\d+) successfully added", response).group("pm_id")
        assert pm_id, "Expected response to contain PM successfully added message"
        assert planned_maintenances.get(int(pm_id), None)

    @pytest.mark.parametrize(
        "start_time,end_time,pm_type,match_type,args,expected_error",
        [
            (
                "abc",
                int((now() + timedelta(hours=1)).timestamp()),
                PmType.DEVICE,
                MatchType.EXACT,
                "localhost",
                "illegal from_t (param 1), must be only digits",
            ),
            (
                int((now() + timedelta(hours=1)).timestamp()),
                "abc",
                PmType.DEVICE,
                MatchType.EXACT,
                "localhost",
                "illegal to_t (param 2), must be only digits",
            ),
            (
                int((now() + timedelta(hours=1)).timestamp()),
                int((now() + timedelta(minutes=10)).timestamp()),
                PmType.DEVICE,
                MatchType.EXACT,
                "localhost",
                "ending time is before starting time",
            ),
            (
                int((now() - timedelta(hours=1)).timestamp()),
                int((now() + timedelta(minutes=10)).timestamp()),
                PmType.DEVICE,
                MatchType.EXACT,
                "localhost",
                "starting time is in the past",
            ),
            (
                int((now() + timedelta(minutes=10)).timestamp()),
                int((now() + timedelta(hours=1)).timestamp()),
                "unknown",
                MatchType.EXACT,
                "localhost",
                "unknown PM event type: unknown",
            ),
            (
                int((now() + timedelta(minutes=10)).timestamp()),
                int((now() + timedelta(hours=1)).timestamp()),
                PmType.DEVICE,
                "unknown",
                "localhost",
                "unknown match type: unknown",
            ),
            (
                int((now() + timedelta(minutes=10)).timestamp()),
                int((now() + timedelta(hours=1)).timestamp()),
                PmType.PORTSTATE,
                MatchType.INTF_REGEXP,
                "localhost",
                f"{MatchType.INTF_REGEXP} match type requires two extra arguments: match_device and match_expression",
            ),
            (
                int((now() + timedelta(minutes=10)).timestamp()),
                int((now() + timedelta(hours=1)).timestamp()),
                PmType.DEVICE,
                MatchType.EXACT,
                None,
                f"{MatchType.EXACT} match type requires one extra argument: match_expression",
            ),
        ],
    )
    async def test_when_authenticated_should_not_create_pm_for_invalid_input(
        self, start_time, end_time, pm_type, match_type, args, expected_error, authenticated_protocol
    ):
        message = f"PM ADD {start_time} {end_time} {pm_type} {match_type}"
        if args:
            message = message + " " + args
        await authenticated_protocol.message_received(message)
        response = authenticated_protocol.transport.data_buffer.getvalue().decode("utf-8")

        assert re.search(r"\b500 \b", response), "Expected response to contain status code 500"
        assert expected_error in response, f"Expected response to contain error message {expected_error}"


class TestZino1ServerProtocolPmMatchingCommand:
    async def test_when_authenticated_should_output_matching_devices(
        self, authenticated_protocol, state_with_localhost, active_device_pm
    ):
        authenticated_protocol._state = state_with_localhost
        active_device_pm.match_expression = "localhost"
        planned_maintenances = authenticated_protocol._state.planned_maintenances.planned_maintenances
        planned_maintenances[active_device_pm.id] = active_device_pm

        await authenticated_protocol.message_received(f"PM MATCHING {active_device_pm.id}")

        output: str = authenticated_protocol.transport.data_buffer.getvalue().decode()

        output = output[output.find("300 Matching ports/devices follows") :]
        lines = output.splitlines()

        assert any(
            str(active_device_pm.id) in line and active_device_pm.match_device in line and "localhost" in line
            for line in lines
        )

    async def test_when_authenticated_should_not_output_non_matching_devices(
        self, authenticated_protocol, state_with_localhost, active_device_pm
    ):
        authenticated_protocol._state = state_with_localhost
        active_device_pm.match_expression = "not_localhost"
        planned_maintenances = authenticated_protocol._state.planned_maintenances.planned_maintenances
        planned_maintenances[active_device_pm.id] = active_device_pm

        await authenticated_protocol.message_received(f"PM MATCHING {active_device_pm.id}")

        output: str = authenticated_protocol.transport.data_buffer.getvalue().decode()

        output = output[output.find("300 Matching ports/devices follows") :]
        lines = output.splitlines()

        assert not any(
            str(active_device_pm.id) in line and active_device_pm.match_device in line and "localhost" in line
            for line in lines
        )

    async def test_when_authenticated_should_output_matching_ports(
        self, authenticated_protocol, state_with_localhost_with_port, active_portstate_pm
    ):
        authenticated_protocol._state = state_with_localhost_with_port
        active_portstate_pm.match_expression = "eth0"
        planned_maintenances = authenticated_protocol._state.planned_maintenances.planned_maintenances
        planned_maintenances[active_portstate_pm.id] = active_portstate_pm

        await authenticated_protocol.message_received(f"PM MATCHING {active_portstate_pm.id}")

        output: str = authenticated_protocol.transport.data_buffer.getvalue().decode()

        output = output[output.find("300 Matching ports/devices follows") :]
        lines = output.splitlines()

        assert any(
            str(active_portstate_pm.id) in line
            and active_portstate_pm.type in line
            and "localhost" in line
            and "eth0" in line
            for line in lines
        )

    async def test_when_authenticated_should_not_output_non_matching_ports(
        self, authenticated_protocol, state_with_localhost_with_port, active_portstate_pm
    ):
        authenticated_protocol._state = state_with_localhost_with_port
        active_portstate_pm.match_expression = "eth1"
        planned_maintenances = authenticated_protocol._state.planned_maintenances.planned_maintenances
        planned_maintenances[active_portstate_pm.id] = active_portstate_pm

        await authenticated_protocol.message_received(f"PM MATCHING {active_portstate_pm.id}")

        output: str = authenticated_protocol.transport.data_buffer.getvalue().decode()

        output = output[output.find("300 Matching ports/devices follows") :]
        lines = output.splitlines()

        assert not any(
            str(active_portstate_pm.id) in line
            and active_portstate_pm.type in line
            and "localhost" in line
            and "eth0" in line
            for line in lines
        )


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


@pytest.fixture
def authenticated_protocol(buffered_fake_transport) -> Zino1ServerProtocol:
    """Returns a pre-authenticated Zino1ServerProtocol instance with a `buffered_fake_transport`"""
    protocol = Zino1ServerProtocol()
    protocol.connection_made(buffered_fake_transport)
    protocol.user = "fake"
    yield protocol
