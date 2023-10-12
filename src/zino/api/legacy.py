"""Legacy API implementation for Zino 2.0.

The Legacy API from the Tcl-based Zino 1.0 is a 'vaguely SMTP-esque line-based text protocol'.  This module
implements this protocol using asyncio semantics.
"""
import asyncio
import inspect
import logging
from asyncio import Transport
from typing import Optional

_logger = logging.getLogger(__name__)


class Zino1BaseServerProtocol(asyncio.Protocol):
    """Base implementation of the Zino 1 protocol, with a basic command dispatcher for subclasses to utilize.

    This base class implements the basic USER and QUIT commands.
    """

    def __init__(self):
        self.transport: Optional[Transport] = None
        self._authenticated = False

    def connection_made(self, transport: Transport):
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
        if not message:
            return
        _logger.debug("Data received from %s: %r", self.peer_name, message)
        args = message.split(" ")
        self._dispatch_command(*args)

    def _dispatch_command(self, command, *args):
        responder = self._get_responder(command)
        if not responder:
            return self._respond_error(f'unknown command: "{command}"')

        signature = inspect.signature(responder)
        required_args = len(signature.parameters)
        if len(args) != required_args:
            arg_summary = " (" + ", ".join(signature.parameters.keys()) + ")" if signature.parameters else ""
            return self._respond_error(f"{command} needs {required_args} parameters{arg_summary}")

        try:
            return responder(*args)
        except Exception:  # noqa
            _logger.exception("Unhandled exception when responding to %r with %r", command, responder)
            return self._respond_error("internal error")

    @property
    def peer_name(self):
        return self.transport.get_extra_info("peername") if self.transport else None

    @property
    def is_authenticated(self):
        return self._authenticated

    def _get_responder(self, command: str):
        if not command.isalpha():
            return

        func = getattr(self, f"do_{command.lower()}", None)
        if callable(func):
            return func

    def _respond_ok(self, message: Optional[str] = "ok"):
        self._respond(200, message)

    def _respond_error(self, message: str):
        self._respond(500, message)

    def _respond(self, code: int, message: str):
        self._respond_raw(f"{code} {message}")

    def _respond_raw(self, message: str):
        """Encodes and sends a response line to the connected client"""
        self.transport.write(f"{message}\r\n".encode("utf-8"))

    def do_user(self, user: str, response: str):
        """Implements the USER command"""
        if self.is_authenticated:
            return self._respond_error("already authenticated")
        if user == "foo" and response == "bar":
            self._authenticated = True
            return self._respond_ok("welcome")
        else:
            return self._respond_error("bad auth")

    def do_quit(self):
        """Implements the QUIT command"""
        self._respond(205, "Bye")
        self.transport.close()
