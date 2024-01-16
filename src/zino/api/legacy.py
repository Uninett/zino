"""Legacy API implementation for Zino 2.0.

The Legacy API from the Tcl-based Zino 1.0 is a 'vaguely SMTP-esque line-based text protocol'.  This module
implements this protocol using asyncio semantics.
"""
import asyncio
import inspect
import logging
import re
import textwrap
from functools import wraps
from pathlib import Path
from typing import Callable, List, Optional, Union

from zino import version
from zino.api import auth
from zino.state import ZinoState
from zino.statemodels import Event, EventState

_logger = logging.getLogger(__name__)


def requires_authentication(func: Callable) -> Callable:
    """Decorates command responder methods to signal that they require the user to be authenticated"""
    func.requires_authentication = True
    return func


class Zino1BaseServerProtocol(asyncio.Protocol):
    """Base implementation of the Zino 1 protocol, with a basic command dispatcher for subclasses to utilize."""

    def __init__(self, state: Optional[ZinoState] = None, secrets_file: Optional[Union[Path, str]] = "secrets"):
        """Initializes a protocol instance.

        :param state: An optional reference to a running Zino state that this server should be based on.  If omitted,
                      this protocol will create and work on an empty state object.
        :param secrets_file: An optional alternative path to the file containing users and their secrets.
        """
        self.transport: Optional[asyncio.Transport] = None
        self._authenticated_as: Optional[str] = None
        self._current_task: asyncio.Task = None
        self._multiline_future: asyncio.Future = None
        self._multiline_buffer: List[str] = []
        self._authentication_challenge: Optional[str] = None

        self._state = state if state is not None else ZinoState()
        self._secrets_file = secrets_file

    @property
    def peer_name(self) -> str:
        return self.transport.get_extra_info("peername") if self.transport else None

    @property
    def is_authenticated(self) -> bool:
        return bool(self._authenticated_as)

    @property
    def user(self) -> Optional[str]:
        """Returns the username of the authenticated user"""
        return self._authenticated_as

    @user.setter
    def user(self, user_name: str):
        self._authenticated_as = user_name

    def connection_made(self, transport: asyncio.Transport):
        self.transport = transport
        _logger.debug("New server connection from %s", self.peer_name)
        self._authentication_challenge = auth.get_challenge()
        self._respond_ok(f"{self._authentication_challenge} Hello, there")

    def data_received(self, data):
        try:
            message = data.decode().rstrip("\r\n")
        except UnicodeDecodeError:
            _logger.error("Received garbage server input from %s: %r", self.peer_name, data)
            self.transport.close()
            return
        _logger.debug("Data received from %s: %r", self.peer_name, message)

        if self._multiline_future:
            if message == ".":
                self._multiline_future.set_result(self._multiline_buffer.copy())
                self._multiline_buffer = []
            else:
                self._multiline_buffer.append(message)
            return

        if not message:
            return
        args = message.split(" ")
        return self._dispatch_command(*args)

    def _dispatch_command(self, command, *args):
        responder = self._get_responder(command)
        if not responder:
            return self._respond_error(f'unknown command: "{command}"')

        if getattr(responder, "requires_authentication", False) and not self.is_authenticated:
            return self._respond_error("Not authenticated")

        required_args = inspect.signature(responder).parameters
        if len(args) != len(required_args):
            arg_summary = " (" + ", ".join(required_args.keys()) + ")" if required_args else ""
            return self._respond_error(f"{command} needs {len(required_args)} parameters{arg_summary}")

        self._current_task = asyncio.create_task(self._run_async_responder(command, responder, *args))
        return self._current_task

    async def _run_async_responder(self, command: str, responder: Callable, *args):
        """Runs a command responder function asynchronously, ensuring that unhandled exceptions are dealt with"""
        try:
            await asyncio.ensure_future(responder(*args))
        except Exception as error:  # noqa
            _logger.exception("unhandled exception raised during processing of %s command: %r", command, error)
            self._respond(500, "internal error")
        finally:
            self._current_task = None

    def _get_responder(self, command: str):
        if not command.isalpha():
            return

        func = getattr(self, f"do_{command.lower()}", None)
        if callable(func):
            return func

    def _get_all_responders(self) -> dict[str, Callable]:
        eligible = {
            name: getattr(self, name) for name in dir(self) if name.startswith("do_") and callable(getattr(self, name))
        }
        commands = {name: re.sub(r"^do_", "", name).upper() for name in eligible}
        return {commands[name]: responder for name, responder in eligible.items()}

    def _read_multiline(self) -> asyncio.Future:
        """Sets the protocol in multline input mode and returns a Future that will trigger once multi-line input is
        complete.
        """
        loop = asyncio.get_running_loop()
        self._multiline_future = loop.create_future()
        self._multiline_future.add_done_callback(self._end_multiline_input_mode)
        return self._multiline_future

    def _end_multiline_input_mode(self, future: asyncio.Future):
        if future is self._multiline_future:
            self._multiline_future = None

    def _respond_ok(self, message: Optional[str] = "ok"):
        self._respond(200, message)

    def _respond_error(self, message: str):
        self._respond(500, message)

    def _respond_multiline(self, code: int, messages: list[str]):
        for index, message in enumerate(messages):
            out = f"{code}- {message}" if index < len(messages) - 1 else f"{code}  {message}"
            self._respond_raw(out)

    def _respond(self, code: int, message: str):
        self._respond_raw(f"{code} {message}")

    def _respond_raw(self, message: str):
        """Encodes and sends a response line to the connected client"""
        self.transport.write(f"{message}\r\n".encode("utf-8"))


class Zino1ServerProtocol(Zino1BaseServerProtocol):
    """Implements the actual working subcommands of the Zino 1 legacy server protocol"""

    async def do_user(self, user: str, response: str):
        """Implements the USER command"""
        if self.is_authenticated:
            return self._respond_error("already authenticated")
        try:
            auth.authenticate(
                user=user, response=response, challenge=self._authentication_challenge, secrets_file=self._secrets_file
            )
        except auth.AuthenticationFailure as error:
            return self._respond_error(error)
        else:
            self.user = user
            return self._respond_ok()

    async def do_quit(self):
        """Implements the QUIT command"""
        self._respond(205, "Bye")
        self.transport.close()

    async def do_help(self):
        responders = self._get_all_responders()
        if not self.is_authenticated:
            responders = {
                name: func for name, func in responders.items() if not getattr(func, "requires_authentication", False)
            }

        commands = " ".join(sorted(responders))
        self._respond_multiline(200, ["commands are:"] + textwrap.wrap(commands, width=56))

    async def do_version(self):
        self._respond(200, f"zino version is {version.__version__}")

    @requires_authentication
    async def do_caseids(self):
        self._respond(304, "list of active cases follows, terminated with '.'")
        for event_id in sorted(self._state.events.events):
            self._respond_raw(str(event_id))
        self._respond_raw(".")

    def _translate_case_id_to_event(responder: callable):  # noqa
        """Decorates any command that works with events/cases, adding verification of the incoming case_id argument
        and translation to an actual Event object.
        """

        @wraps(responder)
        def _verify(self, case_id: Union[str, int], *args, **kwargs):
            try:
                case_id = int(case_id)
                event = self._state.events[case_id]
            except (ValueError, KeyError):
                return self._respond_error(f'event "{case_id}" does not exist')
            return responder(self, event, *args, **kwargs)

        return _verify

    @requires_authentication
    @_translate_case_id_to_event
    async def do_getattrs(self, event: Event):
        self._respond(303, "simple attributes follow, terminated with '.'")
        attrs = event.model_dump_simple_attrs()
        for attr, value in attrs.items():
            self._respond_raw(f"{attr}: {value}")

        self._respond_raw(".")

    @requires_authentication
    @_translate_case_id_to_event
    async def do_gethist(self, event: Event):
        self._respond(301, "history follows, terminated with '.'")
        for history in event.history:
            for line in history.model_dump_legacy():
                self._respond_raw(line)

        self._respond_raw(".")

    @requires_authentication
    @_translate_case_id_to_event
    async def do_getlog(self, event: Event):
        self._respond(300, "log follows, terminated with '.'")
        for log in event.log:
            for line in log.model_dump_legacy():
                self._respond_raw(line)

        self._respond_raw(".")

    @requires_authentication
    @_translate_case_id_to_event
    async def do_addhist(self, event: Event):
        """Implements the ADDHIST API command.

        ADDHIST lets a user add a multi-line message to the event history.  The stored messaged will be prefixed
        by the authenticated user's name on a single line.  Example session for the user `ford`:

        ```
        ADDHIST 160448
        302 please provide new history entry, terminate with '.'
        time is an illusion,
        lunchtime doubly so
        .
        200 ok
        GETHIST 160448
        301 history follows, terminated with '.'
        1697635024 state change embryonic -> open (monitor)
        1697637757 ford
         time is an illusion,
         lunchtime doubly so

        .
        ```
        """
        self._respond(302, "please provide new history entry, terminate with '.'")
        data = await self._read_multiline()
        message = f"{self.user}\n" + "\n".join(line.strip() for line in data)
        event.add_history(message)
        _logger.debug("id %s history added: %r", event.id, message)

        self._respond_ok()

    @requires_authentication
    @_translate_case_id_to_event
    async def do_setstate(self, event: Event, state: str):
        """Sets the state of an event."""
        try:
            event_state = EventState(state)
        except ValueError:
            allowable_states = ", ".join(s.value for s in EventState)
            return self._respond_error(f"state must be one of {allowable_states}")

        out_event = self._state.events.checkout(event.id)
        out_event.set_state(event_state, user=self.user)
        self._state.events.commit(out_event)

        return self._respond_ok()


class ZinoTestProtocol(Zino1ServerProtocol):
    """Extended Zino 1 server protocol with test commands added in"""

    @requires_authentication
    async def do_authtest(self):
        """Implements an AUTHTEST command that did not exist in the Zino 1 protocol. This is just used for verification
        of connection authentication status during development.
        """
        return self._respond_ok()

    async def do_multitest(self):
        """Implements an MULTITEST command that did not exist in the Zino 1 protocol. This is just used for testing
        that multiline input mode works as expected during development.
        """
        self._respond(302, "please provide test input, terminate with '.'")
        data = await self._read_multiline()
        _logger.debug("Received MULTITEST multiline data from %s: %r", self.peer_name, data)
        self._respond_ok()

    async def do_raiseerror(self):
        """Implements a RAISEERROR command that did not exist in the Zino 1 protocol. This is just used for testing
        that exceptions that go unhandled by a command responder is handled by the protocol engine.
        """
        1 / 0  # noqa
