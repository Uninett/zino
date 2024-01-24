"""Notification channel implementation for Zino 2.0.

Notification channels are currently part of the legacy API from the Tcl-based Zino 1.0.  They are a simple text-based,
line-oriented protocol.  Clients are not expected to send any data to a notification channel, only receive data from
the server.
"""
import asyncio
import logging
from typing import TYPE_CHECKING, Any, Iterator, NamedTuple, Optional

from zino.api import auth
from zino.state import ZinoState
from zino.statemodels import Event, EventState

if TYPE_CHECKING:
    from zino.api.legacy import Zino1ServerProtocol
    from zino.api.server import ZinoServer

_logger = logging.getLogger(__name__)


class Notification(NamedTuple):
    """Represents the contents of a single notification"""

    event_id: int
    change_type: str
    value: Any


class Zino1NotificationProtocol(asyncio.Protocol):
    """Basic implementation of the Zino 1 notification protocol"""

    def __init__(self, server: Optional["ZinoServer"] = None, state: Optional[ZinoState] = None):
        """Initializes a protocol instance.

        :param server: An optional instance of `ZinoServer`.
        :param state: An optional reference to a running Zino state that this server should be based on.  If omitted,
                      this protocol will create and work on an empty state object.
        """
        self.server = server
        self.transport: Optional[asyncio.Transport] = None
        self.nonce: Optional[str] = None

        self._state = state if state is not None else ZinoState()
        self._tied_to: "Zino1ServerProtocol" = None

    @property
    def peer_name(self) -> Optional[str]:
        return self.transport.get_extra_info("peername") if self.transport else None

    def connection_made(self, transport: asyncio.Transport):
        self.transport = transport
        _logger.debug("New notification channel from %s", self.peer_name)
        self.nonce = auth.get_challenge()  # Challenges are also useful as nonces
        if self.server:
            self.server.notification_channels[self.nonce] = self
        self._respond_raw(self.nonce)

    def connection_lost(self, exc: Optional[Exception]) -> None:
        _logger.info("Lost connection from %s: %s", self.peer_name, exc)
        if self.server:
            del self.server.notification_channels[self.nonce]

    def goodbye(self):
        """Called by the tied server channel when that closes to gracefully close this channel too"""
        self._respond_raw("Normal quit from client, closing down")
        self.transport.close()

    @property
    def tied_to(self) -> Optional["Zino1ServerProtocol"]:
        return self._tied_to

    @tied_to.setter
    def tied_to(self, client: "Zino1ServerProtocol") -> None:
        self._tied_to = client

    def notify(self, notification: Notification):
        """Sends a notification to the connected client"""
        self._respond_raw(f"{notification.event_id} {notification.change_type} {notification.value}")

    def _respond_raw(self, message: str):
        """Encodes and sends a response line to the connected client"""
        self.transport.write(f"{message}\r\n".encode("utf-8"))

    @classmethod
    def build_and_send_notifications(
        cls, server: "ZinoServer", new_event: Event, old_event: Optional[Event] = None
    ) -> None:
        """Prepares and sends notifications for all changes between old_event and new_event to all connected and tied
        notification channels.
        """
        notifications = list(cls.build_notifications(new_event, old_event))
        tied_channels = [channel for channel in server.notification_channels.values() if channel.tied_to]
        _logger.debug("Sending %s notifications to %s tied channels", len(notifications), len(tied_channels))

        for notification in notifications:
            for channel in tied_channels:
                channel.notify(notification)

    @classmethod
    def build_notifications(cls, new_event: Event, old_event: Optional[Event] = None) -> Iterator[Notification]:
        """Generates a sequence of Notification objects from the changes detected between old_event and new_event.

        If `old_event` is `None`, it is assumed the event is brand new, and only the state change from EMBRYONIC
        matters.
        """
        changed = new_event.get_changed_fields(old_event) if old_event else ["state"]

        for attr in changed:
            if attr == "state":
                old_state = EventState.EMBRYONIC if not old_event else old_event.state
                yield Notification(new_event.id, attr, f"{old_state.value} {new_event.state.value}")

            elif attr in ("log", "history"):
                yield Notification(new_event.id, attr, 1)

            else:
                yield Notification(new_event.id, "attr", attr)
