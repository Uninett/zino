"""On-demand starting of straps/nmtrapd SNMP trap multiplexers.

Zino 1 operators never had to start straps themselves: Scotty's Tnm library started it whenever it
failed to connect to one.  This module gives Zino 2 the same behaviour.

The started process is deliberately not supervised.  Both straps and nmtrapd exit by themselves once
their last client disconnects, so their lifetime follows Zino's connection.

See https://github.com/Uninett/zino/issues/549 for background.
"""

import asyncio
import logging
import re
import shlex
from ipaddress import ip_address
from typing import Optional

from zino.config.models import TrapConfiguration

_logger = logging.getLogger(__name__)

DEFAULT_STRAPS_SOCKET = "/tmp/.straps-162"
# Stock straps can only listen at /tmp/.straps-<port>, and stock nmtrapd only on TCP port 1702
STOCK_STRAPS_SOCKET_PATTERN = re.compile(r"^/tmp/\.straps-\d+$")
STOCK_NMTRAPD_PORT = 1702

CONFIG_HINT = "Set multiplexer_command, or set start_multiplexer = false, in the [snmp.trap] section of zino.toml"


class MultiplexerLauncher:
    """Starts a trap multiplexer process when Zino cannot connect to one."""

    def __init__(self, trap_config: TrapConfiguration):
        self.source = trap_config.source
        self.command = trap_config.multiplexer_command or [trap_config.source]
        self._enabled = trap_config.start_multiplexer and can_serve_configured_endpoint(trap_config)
        self._process: Optional[asyncio.subprocess.Process] = None
        self._monitor_task: Optional[asyncio.Task] = None

    async def start(self) -> bool:
        """Starts the multiplexer, unless disabled or a previously started one is still running.

        :return: True if a multiplexer process was started
        """
        if not self._enabled or self._is_running():
            return False

        _logger.info("Starting %s trap multiplexer: %s", self.source, shlex.join(self.command))
        try:
            self._process = await asyncio.create_subprocess_exec(
                *self.command,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError as error:
            _logger.error("Could not start %s trap multiplexer: %s. %s", self.source, error, CONFIG_HINT)
            return False

        self._monitor_task = asyncio.ensure_future(self._monitor(self._process))
        return True

    def log_unreachable(self, error: OSError) -> None:
        """Logs that a started multiplexer could not be connected to.

        :param error: The error from the last connection attempt
        """
        # nmtrapd closes its stderr when forking into the background
        hint = " (nmtrapd reports its errors only to syslog)" if self.source == "nmtrapd" else ""
        _logger.error("Started %s, but could not connect to it: %s%s", shlex.join(self.command), error, hint)

    def _is_running(self) -> bool:
        return self._process is not None and self._process.returncode is None

    async def _monitor(self, process: asyncio.subprocess.Process) -> None:
        """Logs the multiplexer's error output and exit status, which also ensures it is reaped."""
        async for line in process.stderr:
            _logger.warning("%s: %s", self.source, line.decode(errors="replace").rstrip())

        returncode = await process.wait()
        if returncode:
            _logger.warning("%s trap multiplexer exited with status %d", self.source, returncode)
        else:
            # nmtrapd forks into the background, so its initial process always exits like this
            _logger.debug("%s trap multiplexer process exited", self.source)


def can_serve_configured_endpoint(trap_config: TrapConfiguration) -> bool:
    """Checks whether a started multiplexer could serve the endpoint Zino is configured to connect to.

    Endpoints that stock multiplexers cannot serve only cause a warning, since a custom build or
    command might.  A remote nmtrapd host cannot be served by any locally started process.

    :param trap_config: The trap configuration to check
    :return: False if starting a multiplexer would be pointless
    """
    if trap_config.source == "straps":
        socket_path = trap_config.straps_socket or DEFAULT_STRAPS_SOCKET
        if not STOCK_STRAPS_SOCKET_PATTERN.match(socket_path):
            _logger.warning("Stock straps cannot listen at %s, so starting it may not help", socket_path)
        return True

    if not is_local_host(trap_config.nmtrapd_host):
        _logger.warning(
            "nmtrapd_host %s is not a loopback address, so Zino cannot start nmtrapd for it. "
            "Set start_multiplexer = false in the [snmp.trap] section of zino.toml to silence this warning",
            trap_config.nmtrapd_host,
        )
        return False
    if trap_config.nmtrapd_port != STOCK_NMTRAPD_PORT:
        _logger.warning(
            "Stock nmtrapd only listens on port %d, not %d, so starting it may not help",
            STOCK_NMTRAPD_PORT,
            trap_config.nmtrapd_port,
        )
    return True


def is_local_host(host: str) -> bool:
    """Checks whether a host name or address refers to the local host's loopback interface.

    :param host: A host name or IP address
    :return: True if host is "localhost" or a loopback address
    """
    if host == "localhost":
        return True
    try:
        return ip_address(host).is_loopback
    except ValueError:
        return False
