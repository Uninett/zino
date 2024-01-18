"""Notification channel implementation for Zino 2.0.

Notification channels are currently part of the legacy API from the Tcl-based Zino 1.0, and is a simple text-based,
line-oriented protocol.  Clients are not expected to send any data to a notification channel, only receive data from
the server.
"""
import asyncio
import logging
from typing import TYPE_CHECKING, Any, Optional

from zino.api import auth
from zino.state import ZinoState

if TYPE_CHECKING:
    from zino.api.legacy import Zino1ServerProtocol
    from zino.api.server import ZinoServer

_logger = logging.getLogger(__name__)


class Zino1NotificationProtocol(asyncio.Protocol):
    """Basic implementation of the Zino 1 notification protocol"""

    def __init__(self, server: Optional["ZinoServer"] = None, state: Optional[ZinoState] = None):
        """Initializes a protocol instance.

        :param state: An optional reference to a running Zino state that this server should be based on.  If omitted,
                      this protocol will create and work on an empty state object.
        """
        self.server = server
        self.transport: Optional[asyncio.Transport] = None
        self.nonce: Optional[str] = None

        self._state = state if state is not None else ZinoState()
        self._tied_to: "Zino1ServerProtocol" = None

    @property
    def peer_name(self) -> str:
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

    def _notify(self, event_id: int, change_type: str, value: Any):
        self._respond_raw(f"{event_id} {change_type} {value}")

    def _respond_raw(self, message: str):
        """Encodes and sends a response line to the connected client"""
        self.transport.write(f"{message}\r\n".encode("utf-8"))
