"""SNMP trap reception via straps/nmtrapd trap multiplexer.

This module provides an alternative trap receiver that reads SNMP trap packets from a straps (UNIX
domain socket) or nmtrapd (TCP) trap multiplexer, instead of binding directly to a UDP port.

The straps/nmtrapd multiplexer runs as root and binds to UDP port 162.  It re-broadcasts incoming
raw SNMP trap packets to connected clients, prefixed with a header containing the original sender's
IP address, port, and the length of the SNMP packet data.  This allows multiple unprivileged
programs to receive traps simultaneously.

See https://github.com/Uninett/zino/issues/362 for background.
"""

import asyncio
import logging
import struct
import time
from ipaddress import IPv4Address
from typing import Dict, Optional

from netsnmpy.trapsession import parse_raw_trap

import zino.state
from zino.config.models import PollDevice, TrapConfiguration
from zino.trapd.base import TrapReceiverBase
from zino.trapd.netsnmpy_backend import NetsnmpTrapProcessorMixin

_logger = logging.getLogger(__name__)

# Watchdog defaults (inspired by Zino 1's TrapWatchdog in trap.tcl)
WATCHDOG_CHECK_INTERVAL = 60  # seconds
WATCHDOG_SILENCE_THRESHOLD = 300  # seconds (5 minutes)

# Reconnect backoff on connection loss
RECONNECT_BASE_DELAY = 1  # seconds
RECONNECT_MAX_DELAY = 60  # seconds


class StrapsFrameReader:
    """Reads straps-framed SNMP trap packets from an asyncio StreamReader.

    straps uses a 10-byte header:
    - 4 bytes: sender IP address (network byte order)
    - 2 bytes: sender port (network byte order)
    - 4 bytes: SNMP packet length (host byte order)
    """

    HEADER_SIZE = 10

    async def read_frame(self, reader: asyncio.StreamReader) -> tuple[IPv4Address, int, bytes]:
        """Reads a single framed trap packet from the stream.

        :return: Tuple of (source_address, source_port, raw_pdu_bytes).
        :raises asyncio.IncompleteReadError: If the connection is closed mid-frame.
        """
        header = await reader.readexactly(self.HEADER_SIZE)
        addr_bytes, port = struct.unpack("!4sH", header[:6])
        (length,) = struct.unpack("=I", header[6:10])
        source_addr = IPv4Address(addr_bytes)
        pdu_data = await reader.readexactly(length)
        return source_addr, port, pdu_data


class NmtrapdFrameReader:
    """Reads nmtrapd-framed SNMP trap packets from an asyncio StreamReader.

    nmtrapd uses a 12-byte header:
    - 1 byte: version (always 0)
    - 1 byte: unused (always 0)
    - 2 bytes: sender port (network byte order)
    - 4 bytes: sender IP address (network byte order)
    - 4 bytes: SNMP packet length (network byte order)
    """

    HEADER_SIZE = 12

    async def read_frame(self, reader: asyncio.StreamReader) -> tuple[IPv4Address, int, bytes]:
        """Reads a single framed trap packet from the stream.

        :return: Tuple of (source_address, source_port, raw_pdu_bytes).
        :raises asyncio.IncompleteReadError: If the connection is closed mid-frame.
        """
        header = await reader.readexactly(self.HEADER_SIZE)
        _version, _unused, port, addr_int, length = struct.unpack("!BBHII", header)
        source_addr = IPv4Address(addr_int)
        pdu_data = await reader.readexactly(length)
        return source_addr, port, pdu_data


class StrapsTrapReceiver(NetsnmpTrapProcessorMixin, TrapReceiverBase):
    """Trap receiver that reads from a straps/nmtrapd SNMP trap multiplexer.

    Instead of binding directly to a UDP port, this receiver connects to a UNIX domain socket
    (straps) or TCP socket (nmtrapd) and reads pre-framed raw SNMP trap packets.  The raw packets
    are decoded using Net-SNMP's ``snmp_parse()`` via netsnmpy's ``parse_raw_trap()``, then
    processed through the same pipeline as the direct UDP receiver.
    """

    def __init__(
        self,
        trap_config: TrapConfiguration,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        state: Optional[zino.state.ZinoState] = None,
        polldevs: Optional[Dict[str, PollDevice]] = None,
    ):
        super().__init__(loop=loop, state=state, polldevs=polldevs)
        self._trap_config = trap_config
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._reader_task: Optional[asyncio.Task] = None
        self._watchdog_task: Optional[asyncio.Task] = None
        self._last_trap_time: float = time.monotonic()
        self._reconnect_failures: int = 0
        self._closing: bool = False

        if trap_config.source == "straps":
            self._frame_reader = StrapsFrameReader()
        else:
            self._frame_reader = NmtrapdFrameReader()

    # -- Public API --

    async def open(self):
        """Starts the straps/nmtrapd receiver.

        The initial connection to the multiplexer is attempted in the background, so Zino can
        start even if the multiplexer is not yet available.
        """
        self._reader_task = asyncio.ensure_future(self._read_loop())
        self._watchdog_task = asyncio.ensure_future(self._watchdog_loop())

    def close(self):
        """Closes the socket connection and stops the reader task."""
        self._closing = True
        if self._reader_task and not self._reader_task.done():
            self._reader_task.cancel()
        if self._watchdog_task and not self._watchdog_task.done():
            self._watchdog_task.cancel()
        self._close_connection()

    # -- Main loops (started by open) --

    async def _read_loop(self):
        """Continuously reads and processes trap frames from the multiplexer socket.

        When the connection is lost, immediately attempts to reconnect with exponential backoff.
        """
        while not self._closing:
            if self._reader is None:
                await self._reconnect_with_backoff()
                continue
            try:
                source_addr, source_port, pdu_data = await self._frame_reader.read_frame(self._reader)
                self._last_trap_time = time.monotonic()
                self._reconnect_failures = 0
                self._process_raw_trap(pdu_data, source_addr)
            except asyncio.IncompleteReadError:
                if self._closing:
                    return
                _logger.warning("Connection to %s multiplexer lost (EOF)", self._trap_config.source)
                await self._reconnect_with_backoff()
            except Exception:  # noqa: BLE001
                if self._closing:
                    return
                _logger.exception("Error reading from %s multiplexer", self._trap_config.source)
                await self._reconnect_with_backoff()

    def _process_raw_trap(self, pdu_data: bytes, source_addr: IPv4Address):
        """Parses a raw SNMP PDU and processes it through the standard trap pipeline."""
        try:
            trap = parse_raw_trap(pdu_data, source_addr)
        except ValueError:
            _logger.warning("Failed to parse raw SNMP PDU from %s (length %d)", source_addr, len(pdu_data))
            return
        self.process_snmp_trap(trap)

    async def _reconnect_with_backoff(self):
        """Attempts to reconnect to the multiplexer with exponential backoff."""
        delay = RECONNECT_BASE_DELAY
        while not self._closing:
            try:
                _logger.info("Reconnecting to %s in %ds...", self._trap_config.source, delay)
                await asyncio.sleep(delay)
                if self._closing:
                    return
                await self._connect()
                _logger.info("Reconnected to %s multiplexer", self._trap_config.source)
                return
            except OSError as error:
                _logger.warning("Reconnect to %s failed: %s", self._trap_config.source, error)
                delay = min(delay * 2, RECONNECT_MAX_DELAY)

    async def _watchdog_loop(self):
        """Periodically checks for trap reception silence and reconnects if needed.

        Inspired by Zino 1's TrapWatchdog (trap.tcl): if no trap has been received for more than 5
        minutes, tear down and re-establish the connection.  The failure counter resets when traps
        start flowing again.
        """
        while not self._closing:
            await asyncio.sleep(WATCHDOG_CHECK_INTERVAL)
            if self._closing:
                return

            elapsed = time.monotonic() - self._last_trap_time
            if elapsed < WATCHDOG_SILENCE_THRESHOLD:
                _logger.debug("TrapWatchdog: traps OK (last received %.0fs ago)", elapsed)
                continue

            _logger.warning(
                "TrapWatchdog: no SNMP traps received for %.0fs, reconnecting to %s",
                elapsed,
                self._trap_config.source,
            )
            self._reconnect_failures += 1

            if self._reader_task and not self._reader_task.done():
                self._reader_task.cancel()
                try:
                    await self._reader_task
                except asyncio.CancelledError:
                    pass  # Expected: we just cancelled this task

            try:
                await self._connect()
                self._reader_task = asyncio.ensure_future(self._read_loop())
            except OSError as error:
                _logger.error(
                    "TrapWatchdog: failed to reconnect to %s: %s",
                    self._trap_config.source,
                    error,
                )

    # -- Connection management (used by the above) --

    async def _connect(self):
        """Establishes a connection to the straps/nmtrapd socket."""
        self._close_connection()

        if self._trap_config.source == "straps":
            socket_path = self._trap_config.straps_socket or "/tmp/.straps-162"
            _logger.info("Connecting to straps UNIX socket at %s", socket_path)
            self._reader, self._writer = await asyncio.open_unix_connection(socket_path)
        else:
            host = self._trap_config.nmtrapd_host
            port = self._trap_config.nmtrapd_port
            _logger.info("Connecting to nmtrapd at %s:%d", host, port)
            self._reader, self._writer = await asyncio.open_connection(host, port)

        self._last_trap_time = time.monotonic()
        self._reconnect_failures = 0
        _logger.info("Receiving SNMP traps via %s multiplexer", self._trap_config.source)

    def _close_connection(self):
        """Closes the current socket connection, if any."""
        if self._writer:
            try:
                self._writer.close()
            except Exception:  # noqa: BLE001
                pass
            self._writer = None
        self._reader = None
