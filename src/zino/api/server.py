import logging
from asyncio import AbstractEventLoop

from zino.api.legacy import Zino1ServerProtocol, ZinoTestProtocol
from zino.api.notify import Zino1NotificationProtocol
from zino.state import ZinoState

_logger = logging.getLogger(__name__)


class ZinoServer:
    """Represents the two asyncio servers that work in tandem to implement the Zino 1 legacy API:

    Port 8001 is the text-based command interface.
    Port 8002 is the text-based notification interface.
    """

    API_PORT = 8001
    NOTIFY_PORT = 8002

    def __init__(self, loop: AbstractEventLoop, state: ZinoState):
        self._loop = loop
        self.state: ZinoState = state
        self.active_clients: set[Zino1ServerProtocol] = set()
        self.notification_channels: dict[str, Zino1NotificationProtocol] = {}
        self.notify_server = self.api_server = None

    def serve(self, address: str = "127.0.0.1"):
        """Sets up the two asyncio servers to serve in tandem 'forever'"""
        api_coroutine = self._loop.create_server(
            lambda: ZinoTestProtocol(server=self, state=self.state), address, self.API_PORT
        )
        self.api_server = self._loop.run_until_complete(api_coroutine)
        _logger.info("Serving API on %r", self.api_server.sockets[0].getsockname())

        notify_coroutine = self._loop.create_server(
            lambda: Zino1NotificationProtocol(server=self, state=self.state), address, self.NOTIFY_PORT
        )
        self.notify_server = self._loop.run_until_complete(notify_coroutine)
        _logger.info("Serving notifications on %r", self.notify_server.sockets[0].getsockname())
