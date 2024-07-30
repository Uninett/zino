"""Legacy API implementation for Zino 2.0.

The Legacy API from the Tcl-based Zino 1.0 is a 'vaguely SMTP-esque line-based text protocol'.  This module
implements this protocol using asyncio semantics.
"""

import asyncio
import inspect
import logging
import re
import textwrap
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path
from typing import TYPE_CHECKING, Callable, List, NamedTuple, Optional, Union

from zino import version
from zino.api import auth
from zino.api.notify import Zino1NotificationProtocol
from zino.scheduler import get_scheduler
from zino.state import ZinoState, config
from zino.statemodels import (
    ClosedEventError,
    DeviceMaintenance,
    Event,
    EventState,
    MatchType,
    PlannedMaintenance,
    PortStateMaintenance,
)
from zino.tasks import run_all_tasks
from zino.tasks.linkstatetask import LinkStateTask
from zino.time import now

if TYPE_CHECKING:
    from zino.api.server import ZinoServer

_logger = logging.getLogger(__name__)


class Responder(NamedTuple):
    """A record that maps a command "name" and a regexp pattern to a function"""

    name: str
    pattern: re.Pattern
    function: Callable


def requires_authentication(func: Callable) -> Callable:
    """Decorates command responder methods to signal that they require the user to be authenticated"""
    func.requires_authentication = True
    return func


class Zino1BaseServerProtocol(asyncio.Protocol):
    """Base implementation of the Zino 1 protocol, with a basic command dispatcher for subclasses to utilize."""

    def __init__(
        self,
        server: Optional["ZinoServer"] = None,
        state: Optional[ZinoState] = None,
        secrets_file: Optional[Union[Path, str]] = None,
    ):
        """Initializes a protocol instance.

        :param server: An optional instance of `ZinoServer`.
        :param state: An optional reference to a running Zino state that this server should be based on.  If omitted,
                      this protocol will create and work on an empty state object.
        :param secrets_file: An optional alternative path to the file containing users and their secrets.
        """
        self.server = server
        self.transport: Optional[asyncio.Transport] = None
        self.notification_channel: Optional[Zino1NotificationProtocol] = None
        self._authenticated_as: Optional[str] = None
        self._current_task: asyncio.Task = None
        self._input_buffer = bytearray()
        self._multiline_future: asyncio.Future = None
        self._multiline_buffer: List[str] = []
        self._authentication_challenge: Optional[str] = None
        self._responders = self._get_all_responders()

        self._state = state if state is not None else ZinoState()
        self._secrets_file = secrets_file or config.authentication.file

    @property
    def peer_name(self) -> Optional[str]:
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
        _logger.info("New server connection from %s", self.peer_name)
        if self.server:
            self.server.active_clients.add(self)
        self._authentication_challenge = auth.get_challenge()
        self._respond_ok(f"{self._authentication_challenge} Hello, there")

    def connection_lost(self, exc: Optional[Exception]) -> None:
        _logger.info("Client disconnected: %s", self.peer_name)
        if self.server:
            self.server.active_clients.remove(self)
        if self.notification_channel:
            self.notification_channel.goodbye()

    def data_received(self, data):
        self._input_buffer.extend(data)
        while b"\n" in self._input_buffer:
            line, self._input_buffer = self._input_buffer.split(b"\n", 1)
            try:
                self.message_received(line.rstrip(b"\r").decode())
            except UnicodeDecodeError:
                _logger.error("Received garbage server input from %s: %r", self.peer_name, line)
                self.transport.close()
                return

    def message_received(self, message: str):
        _logger.debug("Message received from %s: %r", self.peer_name, message)

        if self._multiline_future:
            if message == ".":
                self._multiline_future.set_result(self._multiline_buffer.copy())
                self._multiline_buffer = []
            else:
                self._multiline_buffer.append(message)
            return

        if not message:
            return
        return self._dispatch_command(message)

    def _dispatch_command(self, message: str):
        responder, args = self._get_responder(message)
        if not responder:
            return self._respond_error(f'unknown command: "{message}"')

        if getattr(responder.function, "requires_authentication", False) and not self.is_authenticated:
            return self._respond_error("Not authenticated")

        required_args = {
            name: param
            for name, param in inspect.signature(responder.function).parameters.items()
            if param.kind == param.POSITIONAL_OR_KEYWORD
        }
        has_variable_args = any(
            param.kind == param.VAR_POSITIONAL for param in inspect.signature(responder.function).parameters.values()
        )
        if len(args) < len(required_args):
            arg_summary = " (" + ", ".join(required_args.keys()) + ")" if required_args else ""
            return self._respond_error(f"{responder.name} needs {len(required_args)} parameters{arg_summary}")
        elif not has_variable_args and len(args) > len(required_args):
            garbage_args = args[len(required_args) :]
            _logger.debug("client %s sent %r, ignoring garbage args at end: %r", self.peer_name, args, garbage_args)
            args = args[: len(required_args)]

        self._current_task = asyncio.create_task(self._run_async_responder(responder.name, responder.function, *args))
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

    def _get_responder(self, message: str) -> tuple[Optional[Responder], List[str]]:
        matches = ((responder.pattern.match(message), responder) for responder in self._responders.values())
        matches = ((match, responder) for match, responder in matches if match)
        # for multiple matches, always match the longest command first:
        matches = sorted(matches, key=lambda x: len(x[0].group("command")), reverse=True)
        for match, responder in matches:
            args = match.group("args")
            args = args.split(" ") if args else []
            return responder, args
        return None, []

    def _get_all_responders(self) -> dict[str, Responder]:
        eligible = {
            name: getattr(self, name) for name in dir(self) if name.startswith("do_") and callable(getattr(self, name))
        }
        commands = {name: re.sub(r"^do_", "", name).upper().replace("_", " ") for name in eligible}
        return {
            commands[name]: Responder(
                commands[name], re.compile(rf"(?P<command>{commands[name]})\b\s*(?P<args>.*)", re.IGNORECASE), responder
            )
            for name, responder in eligible.items()
        }

    def _get_top_level_responders(self) -> dict[str, Responder]:
        return {name: responder for name, responder in self._responders.items() if " " not in responder.name}

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
        """Lists all available top-level API commands"""
        top_level_responders = self._get_top_level_responders()
        authorized_responders = (
            responder
            for responder in top_level_responders.values()
            if self.is_authenticated or not getattr(responder.function, "requires_authentication", False)
        )

        commands = " ".join(sorted(responder.name for responder in authorized_responders))
        self._respond_multiline(200, ["commands are:"] + textwrap.wrap(commands, width=56))

    async def do_version(self):
        self._respond(200, f"zino version is {version.__version__}")

    @requires_authentication
    async def do_caseids(self):
        self._respond(304, "list of active cases follows, terminated with '.'")
        events = self._state.events.events
        for event_id, event in sorted(events.items()):
            if event.state != EventState.CLOSED:
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
                self._respond_error(f'event "{case_id}" does not exist')
                response = asyncio.get_running_loop().create_future()
                response.set_result(None)
                return response
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
        out_event = self._state.events.checkout(event.id)
        out_event.add_history(message)
        self._state.events.commit(out_event)
        _logger.debug("id %s history added: %r", out_event.id, message)

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
        try:
            out_event.set_state(event_state, user=self.user)
        except ClosedEventError:
            return self._respond_error(f"Cannot reopen closed event {event.id}")
        self._state.events.commit(out_event)

        return self._respond_ok()

    @requires_authentication
    async def do_community(self, router_name: str):
        from zino.state import polldevs

        if router_name in polldevs:
            device = polldevs[router_name]
            self._respond(201, f"{device.community}")
        else:
            self._respond_error("router unknown")

    @requires_authentication
    async def do_ntie(self, nonce: str):
        """Implements the NTIE command that ties together this session with a notification channel."""
        try:
            channel = self.server.notification_channels[nonce]
        except (AttributeError, KeyError):
            return self._respond_error("Could not find your notify socket")

        self.notification_channel = channel
        channel.tied_to = self
        _logger.info("Client %s tied to notification channel %s", self.peer_name, channel.peer_name)

        return self._respond_ok()

    @requires_authentication
    async def do_pollrtr(self, router_name: str):
        from zino.state import polldevs

        device = polldevs.get(router_name, None)
        if not device:
            return self._respond_error(f"Router {router_name} unknown")

        scheduler = get_scheduler()

        job_name = f"{router_name}-api-triggered"
        scheduler.add_job(
            func=run_all_tasks,
            trigger="date",
            args=(device, self._state),
            run_date=datetime.now(),
            name=job_name,
        )

        return self._respond_ok()

    @requires_authentication
    async def do_pollintf(self, router_name: str, ifindex: Union[str, int]):
        from zino.state import polldevs

        try:
            device = polldevs[router_name]
        except KeyError:
            return self._respond_error(f"Router {router_name} unknown")
        try:
            ifindex = abs(int(ifindex))
        except ValueError:
            return self._respond_error(f"{ifindex} is an invalid ifindex value")

        task = LinkStateTask(device, self._state)
        task.schedule_verification_of_single_port(
            ifindex=ifindex, deadline=timedelta(seconds=0), reason="api-triggered"
        )
        return self._respond_ok()

    @requires_authentication
    async def do_clearflap(self, router_name: str, ifindex: Union[str, int]):
        """Implements a dummy CLEARFLAP command (for now)"""
        from zino.state import polldevs

        try:
            _device = polldevs[router_name]
        except KeyError:
            return self._respond_error(f"Router {router_name} unknown")
        try:
            ifindex = abs(int(ifindex))
        except ValueError:
            return self._respond_error(f"{ifindex} is an invalid ifindex value")

        return self._respond_ok("not implemented")

    def _translate_pm_id_to_pm(responder: callable):  # noqa
        """Decorates any command that works with planned maintenance adding verification of the
        incoming pm_id argument and translation to an actual PlannedMaintenance object.
        """

        @wraps(responder)
        def _verify(self, pm_id: Union[str, int], *args, **kwargs):
            try:
                pm_id = int(pm_id)
                pm = self._state.planned_maintenances[pm_id]
            except (ValueError, KeyError):
                self._respond_error(f'pm "{pm_id}" does not exist')
                response = asyncio.get_running_loop().create_future()
                response.set_result(None)
                return response
            return responder(self, pm, *args, **kwargs)

        return _verify

    @requires_authentication
    async def do_pm(self):
        """Implements the top-level PM command.

        In the original Zino, this has its own dispatcher, and calling it without arguments only results an error.
        """
        return self._respond_error("PM command requires a subcommand")

    @requires_authentication
    async def do_pm_help(self):
        """Lists all available PM sub-commands"""
        responders = (responder for name, responder in self._responders.items() if responder.name.startswith("PM "))
        commands = " ".join(sorted(responder.name.removeprefix("PM ") for responder in responders))
        self._respond_multiline(200, ["PM subcommands are:"] + textwrap.wrap(commands, width=56))

    @requires_authentication
    async def do_pm_list(self):
        self._respond(300, "PM event ids follows, terminated with '.'")
        for id in self._state.planned_maintenances.planned_maintenances:
            self._respond_raw(id)
        self._respond_raw(".")

    @requires_authentication
    @_translate_pm_id_to_pm
    async def do_pm_cancel(self, pm: PlannedMaintenance):
        self._state.planned_maintenances.close_planned_maintenance(pm.id, "PM cancelled", self.user)
        self._respond_ok()

    @requires_authentication
    @_translate_pm_id_to_pm
    async def do_pm_addlog(self, pm: PlannedMaintenance):
        self._respond(302, "please provide new PM log entry, terminate with '.'")
        data = await self._read_multiline()
        message = f"{self.user}\n" + "\n".join(line.strip() for line in data)
        pm.add_log(message)
        self._respond_ok()

    @requires_authentication
    @_translate_pm_id_to_pm
    async def do_pm_log(self, pm: PlannedMaintenance):
        self._respond(300, "log follows, terminated with '.'")
        for log in pm.log:
            for line in log.model_dump_legacy():
                self._respond_raw(line)
        self._respond_raw(".")

    @requires_authentication
    @_translate_pm_id_to_pm
    async def do_pm_details(self, pm: PlannedMaintenance):
        self._respond(200, pm.details())

    @requires_authentication
    async def do_pm_add(self, from_t: Union[str, int], to_t: Union[str, int], pm_type: str, m_type: str, *args: str):
        try:
            start_time = datetime.fromtimestamp(int(from_t), tz=timezone.utc)
        except ValueError:
            return self._respond_error("illegal from_t (param 1), must be only digits")
        try:
            end_time = datetime.fromtimestamp(int(to_t), tz=timezone.utc)
        except ValueError:
            return self._respond_error("illegal to_t (param 2), must be only digits")
        if end_time < start_time:
            return self._respond_error("ending time is before starting time")
        if start_time < now():
            return self._respond_error("starting time is in the past")

        if pm_type == "device":
            pm_class = DeviceMaintenance
        elif pm_type == "portstate":
            pm_class = PortStateMaintenance
        else:
            return self._respond_error(f"unknown PM event type: {pm_type}")

        try:
            match_type = MatchType(m_type)
        except ValueError:
            return self._respond_error(f"unknown match type: {m_type}")

        if match_type == MatchType.INTF_REGEXP:
            if len(args) < 2:
                return self._respond_error(
                    f"{m_type} match type requires two extra arguments: match_device and match_expression"
                )
            match_device = args[0]
            match_expression = args[1]
        else:
            if len(args) < 1:
                return self._respond_error(f"{m_type} match type requires one extra argument: match_expression")
            match_device = None
            match_expression = args[0]

        pm = self._state.planned_maintenances.create_planned_maintenance(
            start_time,
            end_time,
            pm_class,
            match_type,
            match_expression,
            match_device,
        )
        self._respond(200, f"PM id {pm.id} successfully added")

    @requires_authentication
    @_translate_pm_id_to_pm
    async def do_pm_matching(self, pm: PlannedMaintenance):
        matches = pm.get_matching(self._state)
        self._respond(300, "Matching ports/devices follows, terminated with '.'")
        for match in matches:
            output = " ".join(str(i) for i in match)
            self._respond_raw(output)
        self._respond_raw(".")


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
