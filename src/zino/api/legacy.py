"""Legacy API implementation for Zino 2.0.

The Legacy API from the Tcl-based Zino 1.0 is a 'vaguely SMTP-esque line-based text protocol'.  This module
implements this protocol using asyncio semantics.
"""
import asyncio
import inspect
import logging
import re
import textwrap
from typing import Callable, List, Optional

_logger = logging.getLogger(__name__)


def requires_authentication(func: Callable) -> Callable:
    """Decorates command responder methods to signal that they require the user to be authenticated"""
    func.requires_authentication = True
    return func


class Zino1BaseServerProtocol(asyncio.Protocol):
    """Base implementation of the Zino 1 protocol, with a basic command dispatcher for subclasses to utilize."""

    def __init__(self):
        self.transport: Optional[asyncio.Transport] = None
        self._authenticated: bool = False
        self._current_task: asyncio.Task = None
        self._multiline_future: asyncio.Future = None
        self._multiline_buffer: List[str] = []

    @property
    def peer_name(self):
        return self.transport.get_extra_info("peername") if self.transport else None

    @property
    def is_authenticated(self):
        return self._authenticated

    def connection_made(self, transport: asyncio.Transport):
        self.transport = transport
        _logger.debug("New server connection from %s", self.peer_name)
        self._respond_ok("PLACEHOLDER-CHALLENGE Hello, there")

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
        self._dispatch_command(*args)

    def _dispatch_command(self, command, *args):
        responder = self._get_responder(command)
        if not responder:
            return self._respond_error(f'unknown command: "{command}"')

        if getattr(responder, "requires_authentication", False) and not self.is_authenticated:
            return self._respond_error("Not authenticated")

        signature = inspect.signature(responder)
        required_args = len(signature.parameters)
        if len(args) != required_args:
            arg_summary = " (" + ", ".join(signature.parameters.keys()) + ")" if signature.parameters else ""
            return self._respond_error(f"{command} needs {required_args} parameters{arg_summary}")

        try:
            self._current_task = asyncio.ensure_future(responder(*args))
            self._current_task.add_done_callback(self._clear_current_task)
        except Exception:  # noqa
            _logger.exception("Unhandled exception when responding to %r with %r", command, responder)
            return self._respond_error("internal error")

    def _clear_current_task(self, task: asyncio.Task):
        if task is self._current_task:
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
        if user == "foo" and response == "bar":
            self._authenticated = True
            return self._respond_ok("welcome")
        else:
            return self._respond_error("bad auth")

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
