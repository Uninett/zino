"""Socket utilities for the API servers"""

import asyncio
import socket


def enable_keepalive(transport: asyncio.BaseTransport) -> None:
    """Enables TCP keepalive on a transport's socket.

    This lets the operating system eventually detect clients that have vanished without closing their connections,
    such as clients behind a dropped VPN or a NAT that has forgotten the connection.

    :param transport: The transport of an accepted client connection
    """
    sock = transport.get_extra_info("socket")
    if sock is None:
        return
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
