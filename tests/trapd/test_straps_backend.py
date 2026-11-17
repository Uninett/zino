"""Tests for the straps/nmtrapd trap multiplexer backend."""

import asyncio
import ipaddress
import struct
import sys
import time
from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio

from zino.config.models import TrapConfiguration
from zino.state import ZinoState
from zino.trapd.straps_backend import (
    NmtrapdFrameReader,
    StrapsFrameReader,
    StrapsTrapReceiver,
)

# The same BER-encoded SNMPv2c coldStart trap used in netsnmp-cffi tests
SNMPV2C_COLDSTART_TRAP = bytes.fromhex(
    "305402010104067075626c6963a74702034ff374020100020100303a300e06082b060102010103004302"
    "30393017060a2b06010603010104010006092b0601060301010501300f060a2b060102010202010101"
    "02012a"
)

# Stands in for straps: serves one client at the socket path given as argument, then exits once the client disconnects
FAKE_STRAPS = """
import os, socket, sys
server = socket.socket(socket.AF_UNIX)
server.bind(sys.argv[1])
server.listen(1)
server.settimeout(5)
client, _ = server.accept()
client.recv(1)
os.unlink(sys.argv[1])
"""

# Stands in for nmtrapd: forks into the background, closing stderr, then serves one client on the TCP port given as
# argument until it disconnects
FAKE_NMTRAPD = """
import os, socket, sys
if os.fork():
    sys.exit(0)
os.close(2)
server = socket.socket()
server.bind(("127.0.0.1", int(sys.argv[1])))
server.listen(1)
server.settimeout(5)
client, _ = server.accept()
client.recv(1)
"""


class TestStrapsFrameReader:
    async def test_when_reading_valid_frame_then_it_should_extract_source_address(self):
        frame = make_straps_frame("10.0.0.1", 162, SNMPV2C_COLDSTART_TRAP)
        reader = asyncio.StreamReader()
        reader.feed_data(frame)
        addr, port, pdu = await StrapsFrameReader().read_frame(reader)
        assert addr == ipaddress.IPv4Address("10.0.0.1")

    async def test_when_reading_valid_frame_then_it_should_extract_source_port(self):
        frame = make_straps_frame("10.0.0.1", 4242, SNMPV2C_COLDSTART_TRAP)
        reader = asyncio.StreamReader()
        reader.feed_data(frame)
        addr, port, pdu = await StrapsFrameReader().read_frame(reader)
        assert port == 4242

    async def test_when_reading_valid_frame_then_it_should_extract_raw_pdu(self):
        frame = make_straps_frame("10.0.0.1", 162, SNMPV2C_COLDSTART_TRAP)
        reader = asyncio.StreamReader()
        reader.feed_data(frame)
        addr, port, pdu = await StrapsFrameReader().read_frame(reader)
        assert pdu == SNMPV2C_COLDSTART_TRAP

    async def test_when_connection_closes_mid_frame_then_it_should_raise_incomplete_read(self):
        reader = asyncio.StreamReader()
        reader.feed_data(b"\x00\x01\x02")
        reader.feed_eof()
        with pytest.raises(asyncio.IncompleteReadError):
            await StrapsFrameReader().read_frame(reader)


class TestNmtrapdFrameReader:
    async def test_when_reading_valid_frame_then_it_should_extract_source_address(self):
        frame = make_nmtrapd_frame("10.0.0.1", 162, SNMPV2C_COLDSTART_TRAP)
        reader = asyncio.StreamReader()
        reader.feed_data(frame)
        addr, port, pdu = await NmtrapdFrameReader().read_frame(reader)
        assert addr == ipaddress.IPv4Address("10.0.0.1")

    async def test_when_reading_valid_frame_then_it_should_extract_source_port(self):
        frame = make_nmtrapd_frame("10.0.0.1", 4242, SNMPV2C_COLDSTART_TRAP)
        reader = asyncio.StreamReader()
        reader.feed_data(frame)
        addr, port, pdu = await NmtrapdFrameReader().read_frame(reader)
        assert port == 4242

    async def test_when_reading_valid_frame_then_it_should_extract_raw_pdu(self):
        frame = make_nmtrapd_frame("10.0.0.1", 162, SNMPV2C_COLDSTART_TRAP)
        reader = asyncio.StreamReader()
        reader.feed_data(frame)
        addr, port, pdu = await NmtrapdFrameReader().read_frame(reader)
        assert pdu == SNMPV2C_COLDSTART_TRAP

    async def test_when_connection_closes_mid_frame_then_it_should_raise_incomplete_read(self):
        reader = asyncio.StreamReader()
        reader.feed_data(b"\x00\x01\x02")
        reader.feed_eof()
        with pytest.raises(asyncio.IncompleteReadError):
            await NmtrapdFrameReader().read_frame(reader)


class TestStrapsTrapReceiver:
    @pytest.mark.timeout(5)
    async def test_when_connected_to_straps_socket_then_it_should_process_incoming_trap(
        self, straps_unix_server, straps_receiver_with_localhost
    ):
        receiver = straps_receiver_with_localhost
        await receiver._connect()
        receiver._reader_task = asyncio.ensure_future(receiver._read_loop())
        await asyncio.sleep(0.1)
        assert receiver._last_trap_time > 0
        receiver.close()
        await _gather_cancelled(receiver)

    @pytest.mark.timeout(5)
    async def test_when_connected_to_straps_socket_then_it_should_dispatch_trap_from_known_device(
        self, straps_unix_server, straps_receiver_with_localhost
    ):
        receiver = straps_receiver_with_localhost
        dispatched = []
        original_dispatch = receiver.dispatch_trap

        async def capture_dispatch(trap):
            dispatched.append(trap)
            await original_dispatch(trap)

        receiver.dispatch_trap = capture_dispatch
        await receiver._connect()
        receiver._reader_task = asyncio.ensure_future(receiver._read_loop())
        await asyncio.sleep(0.1)
        assert len(dispatched) == 1
        assert dispatched[0].agent.address == ipaddress.IPv4Address("127.0.0.1")
        receiver.close()
        await _gather_cancelled(receiver)

    async def test_when_closing_and_multiplexer_disconnects_then_read_loop_should_exit(self, nonexistent_path):
        config = TrapConfiguration(source="straps", straps_socket=nonexistent_path)
        receiver = StrapsTrapReceiver(trap_config=config, state=ZinoState())

        reader = asyncio.StreamReader()
        reader.feed_eof()
        receiver._reader = reader
        receiver._closing = True
        await receiver._read_loop()

    async def test_when_multiplexer_disconnects_then_reconnect_with_backoff_should_be_called(self, nonexistent_path):
        config = TrapConfiguration(source="straps", straps_socket=nonexistent_path)
        receiver = StrapsTrapReceiver(trap_config=config, state=ZinoState())

        reader = asyncio.StreamReader()
        reader.feed_eof()
        receiver._reader = reader

        mock_reconnect = AsyncMock(side_effect=lambda: setattr(receiver, "_closing", True))
        with patch.object(receiver, "_reconnect_with_backoff", mock_reconnect):
            await receiver._read_loop()
        mock_reconnect.assert_called_once()

    async def test_when_straps_is_unavailable_at_startup_then_open_should_not_raise(self, nonexistent_path):
        config = TrapConfiguration(source="straps", straps_socket=nonexistent_path)
        receiver = StrapsTrapReceiver(trap_config=config, state=ZinoState())

        mock_reconnect = AsyncMock(side_effect=lambda: setattr(receiver, "_closing", True))
        with patch.object(receiver, "_reconnect_with_backoff", mock_reconnect):
            await receiver.open()
            await asyncio.sleep(0.1)
            receiver.close()
            await _gather_cancelled(receiver)

        mock_reconnect.assert_called_once()

    async def test_when_read_loop_hits_generic_exception_then_it_should_attempt_reconnect(self, nonexistent_path):
        config = TrapConfiguration(source="straps", straps_socket=nonexistent_path)
        receiver = StrapsTrapReceiver(trap_config=config, state=ZinoState())
        receiver._reader = asyncio.StreamReader()

        receiver._frame_reader.read_frame = AsyncMock(side_effect=RuntimeError("something broke"))

        mock_reconnect = AsyncMock(side_effect=lambda: setattr(receiver, "_closing", True))
        with patch.object(receiver, "_reconnect_with_backoff", mock_reconnect):
            await receiver._read_loop()
        mock_reconnect.assert_called_once()

    async def test_when_raw_pdu_is_malformed_then_process_raw_trap_should_log_warning(self, nonexistent_path, caplog):
        config = TrapConfiguration(source="straps", straps_socket=nonexistent_path)
        receiver = StrapsTrapReceiver(trap_config=config, state=ZinoState())
        receiver._process_raw_trap(b"\x00\x01\x02", ipaddress.IPv4Address("10.0.0.1"))
        assert "Failed to parse raw SNMP PDU" in caplog.text

    @pytest.mark.timeout(5)
    async def test_when_open_is_called_then_it_should_start_reader_and_watchdog(
        self, straps_unix_server, straps_receiver_with_localhost
    ):
        receiver = straps_receiver_with_localhost
        with (
            patch("zino.trapd.straps_backend.WATCHDOG_CHECK_INTERVAL", 0.1),
            patch("zino.trapd.straps_backend.WATCHDOG_SILENCE_THRESHOLD", 600),
        ):
            await receiver.open()
            await asyncio.sleep(0.1)
            assert receiver._reader_task is not None
            assert receiver._watchdog_task is not None
            assert not receiver._reader_task.done()
            assert not receiver._watchdog_task.done()
            receiver.close()
            await _gather_cancelled(receiver)

    async def test_when_close_is_called_then_it_should_set_closing_and_cancel_tasks(self, nonexistent_path):
        config = TrapConfiguration(source="straps", straps_socket=nonexistent_path)
        receiver = StrapsTrapReceiver(trap_config=config, state=ZinoState())
        receiver._reader_task = asyncio.ensure_future(asyncio.sleep(60))
        receiver._watchdog_task = asyncio.ensure_future(asyncio.sleep(60))
        receiver.close()
        await asyncio.sleep(0)  # Let cancellations propagate
        assert receiver._closing is True
        assert receiver._reader_task.cancelled()
        assert receiver._watchdog_task.cancelled()

    async def test_when_straps_source_is_configured_then_it_should_use_straps_frame_reader(self):
        config = TrapConfiguration(source="straps")
        receiver = StrapsTrapReceiver(trap_config=config, state=ZinoState())
        assert isinstance(receiver._frame_reader, StrapsFrameReader)

    async def test_when_nmtrapd_source_is_configured_then_it_should_use_nmtrapd_frame_reader(self):
        config = TrapConfiguration(source="nmtrapd")
        receiver = StrapsTrapReceiver(trap_config=config, state=ZinoState())
        assert isinstance(receiver._frame_reader, NmtrapdFrameReader)

    @pytest.mark.timeout(5)
    async def test_when_reconnect_fails_then_it_should_retry_multiple_times(self, nonexistent_path):
        config = TrapConfiguration(source="straps", straps_socket=nonexistent_path)
        receiver = StrapsTrapReceiver(trap_config=config, state=ZinoState())

        attempts = []

        async def failing_connect():
            attempts.append(time.monotonic())
            raise OSError("connection refused")

        with (
            patch.object(receiver, "_connect", failing_connect),
            patch("zino.trapd.straps_backend.RECONNECT_BASE_DELAY", 0.1),
            patch("zino.trapd.straps_backend.RECONNECT_MAX_DELAY", 1),
        ):
            task = asyncio.ensure_future(receiver._reconnect_with_backoff())
            await asyncio.sleep(1)
            receiver._closing = True
            await task

        assert len(attempts) >= 3, f"Expected at least 3 reconnect attempts, got {len(attempts)}"

    @pytest.mark.timeout(5)
    async def test_when_watchdog_detects_silence_then_it_should_reconnect(self, nonexistent_path):
        config = TrapConfiguration(source="straps", straps_socket=nonexistent_path)
        receiver = StrapsTrapReceiver(trap_config=config, state=ZinoState())
        receiver._last_trap_time = time.monotonic() - 600
        receiver._reader_task = asyncio.ensure_future(asyncio.sleep(60))

        connect_called = asyncio.Event()

        async def mock_connect():
            connect_called.set()
            receiver._closing = True

        with (
            patch("zino.trapd.straps_backend.WATCHDOG_CHECK_INTERVAL", 0.1),
            patch("zino.trapd.straps_backend.WATCHDOG_SILENCE_THRESHOLD", 1),
            patch.object(receiver, "_connect", mock_connect),
        ):
            receiver._watchdog_task = asyncio.ensure_future(receiver._watchdog_loop())
            await asyncio.sleep(0.5)
            receiver.close()
            await _gather_cancelled(receiver)

        assert connect_called.is_set()

    @pytest.mark.timeout(5)
    async def test_when_traps_are_flowing_then_watchdog_should_not_trigger_reconnect(self, nonexistent_path):
        config = TrapConfiguration(source="straps", straps_socket=nonexistent_path)
        receiver = StrapsTrapReceiver(trap_config=config, state=ZinoState())
        receiver._last_trap_time = time.monotonic()  # Just now — traps are flowing
        receiver._reader_task = asyncio.ensure_future(asyncio.sleep(60))

        connect_called = False

        async def mock_connect():
            nonlocal connect_called
            connect_called = True

        with (
            patch("zino.trapd.straps_backend.WATCHDOG_CHECK_INTERVAL", 0.1),
            patch("zino.trapd.straps_backend.WATCHDOG_SILENCE_THRESHOLD", 600),
            patch.object(receiver, "_connect", mock_connect),
        ):
            receiver._watchdog_task = asyncio.ensure_future(receiver._watchdog_loop())
            await asyncio.sleep(0.5)
            receiver.close()
            await _gather_cancelled(receiver)

        assert not connect_called

    @pytest.mark.timeout(5)
    async def test_when_multiplexer_is_available_then_reconnect_should_establish_connection(
        self, straps_unix_server, straps_receiver_with_localhost
    ):
        receiver = straps_receiver_with_localhost
        await receiver._reconnect_with_backoff()
        # Assert that internal state appears connected
        assert receiver._reader is not None
        receiver._close_connection()

    @pytest.mark.timeout(5)
    async def test_when_watchdog_reconnect_fails_then_it_should_log_error(self, nonexistent_path, caplog):
        config = TrapConfiguration(source="straps", straps_socket=nonexistent_path)
        receiver = StrapsTrapReceiver(trap_config=config, state=ZinoState())
        receiver._last_trap_time = time.monotonic() - 600
        receiver._reader_task = asyncio.ensure_future(asyncio.sleep(60))

        async def failing_connect():
            raise OSError("socket not found")

        with (
            patch("zino.trapd.straps_backend.WATCHDOG_CHECK_INTERVAL", 0.1),
            patch("zino.trapd.straps_backend.WATCHDOG_SILENCE_THRESHOLD", 1),
            patch.object(receiver, "_connect", failing_connect),
        ):
            receiver._watchdog_task = asyncio.ensure_future(receiver._watchdog_loop())
            await asyncio.sleep(0.5)
            receiver.close()
            await _gather_cancelled(receiver)

        assert "failed to reconnect" in caplog.text

    @pytest.mark.timeout(5)
    async def test_when_nmtrapd_connect_is_called_then_it_should_open_tcp_connection(self):
        config = TrapConfiguration(source="nmtrapd", nmtrapd_host="trap.example.com", nmtrapd_port=1702)
        receiver = StrapsTrapReceiver(trap_config=config, state=ZinoState())

        with patch("zino.trapd.straps_backend.asyncio.open_connection", new_callable=AsyncMock) as mock_open:
            mock_open.return_value = (asyncio.StreamReader(), Mock())
            await receiver._connect()
            mock_open.assert_called_once_with("trap.example.com", 1702)
        receiver._close_connection()

    async def test_when_close_connection_is_called_then_writer_should_be_closed(self, nonexistent_path):
        config = TrapConfiguration(source="straps", straps_socket=nonexistent_path)
        receiver = StrapsTrapReceiver(trap_config=config, state=ZinoState())
        mock_writer = Mock()
        receiver._writer = mock_writer
        receiver._reader = asyncio.StreamReader()
        receiver._close_connection()
        mock_writer.close.assert_called_once()
        assert receiver._writer is None
        assert receiver._reader is None


class TestStrapsTrapReceiverStartingMultiplexer:
    @pytest.mark.timeout(5)
    async def test_given_no_multiplexer_is_listening_when_connecting_then_it_should_start_one_and_connect(  # noqa: E501
        self, straps_socket_path
    ):
        config = TrapConfiguration(
            source="straps",
            straps_socket=straps_socket_path,
            multiplexer_command=[sys.executable, "-c", FAKE_STRAPS, straps_socket_path],
        )
        receiver = StrapsTrapReceiver(trap_config=config, state=ZinoState())
        with patch("zino.trapd.straps_backend.STARTUP_CONNECT_INTERVAL", 0.1):
            await receiver._connect()
        assert receiver._reader is not None

        receiver._close_connection()
        await receiver._launcher._monitor_task

    async def test_given_multiplexer_is_already_listening_when_connecting_then_it_should_not_start_another(
        self, straps_unix_server, straps_receiver_with_localhost
    ):
        receiver = straps_receiver_with_localhost
        with patch.object(receiver._launcher, "start", new_callable=AsyncMock) as mock_start:
            await receiver._connect()
        mock_start.assert_not_called()
        receiver._close_connection()

    async def test_given_multiplexer_cannot_be_started_when_connecting_then_it_should_raise(self, nonexistent_path):
        config = TrapConfiguration(
            source="straps", straps_socket=nonexistent_path, multiplexer_command=[nonexistent_path]
        )
        receiver = StrapsTrapReceiver(trap_config=config, state=ZinoState())
        with pytest.raises(OSError):
            await receiver._connect()

    async def test_given_started_multiplexer_never_listens_when_connecting_then_it_should_log_error_and_raise(  # noqa: E501
        self, nonexistent_path, caplog
    ):
        config = TrapConfiguration(
            source="straps", straps_socket=nonexistent_path, multiplexer_command=[sys.executable, "-c", "pass"]
        )
        receiver = StrapsTrapReceiver(trap_config=config, state=ZinoState())
        with patch("zino.trapd.straps_backend.STARTUP_CONNECT_INTERVAL", 0.01), pytest.raises(OSError):
            await receiver._connect()
        assert "could not connect" in caplog.text
        await receiver._launcher._monitor_task

    async def test_given_started_nmtrapd_never_listens_when_connecting_then_error_should_point_at_syslog(
        self, unused_tcp_port, caplog
    ):
        config = TrapConfiguration(
            source="nmtrapd", nmtrapd_port=unused_tcp_port, multiplexer_command=[sys.executable, "-c", "pass"]
        )
        receiver = StrapsTrapReceiver(trap_config=config, state=ZinoState())
        with patch("zino.trapd.straps_backend.STARTUP_CONNECT_INTERVAL", 0.01), pytest.raises(OSError):
            await receiver._connect()
        assert "syslog" in caplog.text
        await receiver._launcher._monitor_task

    @pytest.mark.timeout(5)
    async def test_given_daemonizing_multiplexer_is_not_running_when_reconnecting_then_it_should_be_started_and_connected(  # noqa: E501
        self, unused_tcp_port
    ):
        config = TrapConfiguration(
            source="nmtrapd",
            nmtrapd_port=unused_tcp_port,
            multiplexer_command=[sys.executable, "-c", FAKE_NMTRAPD, str(unused_tcp_port)],
        )
        receiver = StrapsTrapReceiver(trap_config=config, state=ZinoState())
        with (
            patch("zino.trapd.straps_backend.RECONNECT_BASE_DELAY", 0.01),
            patch("zino.trapd.straps_backend.STARTUP_CONNECT_INTERVAL", 0.1),
        ):
            await receiver._reconnect_with_backoff()
        assert receiver._reader is not None

        receiver._close_connection()
        await receiver._launcher._monitor_task


async def _gather_cancelled(receiver: StrapsTrapReceiver):
    """Awaits the receiver's background tasks so cancellations complete."""
    tasks = [t for t in (receiver._reader_task, receiver._watchdog_task) if t and not t.done()]
    if tasks:
        await asyncio.wait(tasks, timeout=1)


def make_straps_frame(addr: str, port: int, pdu: bytes) -> bytes:
    """Builds a straps-formatted frame: addr(4,network) + port(2,network) + length(4,host)."""
    addr_bytes = ipaddress.IPv4Address(addr).packed
    return struct.pack("!4sH", addr_bytes, port) + struct.pack("=I", len(pdu)) + pdu


def make_nmtrapd_frame(addr: str, port: int, pdu: bytes) -> bytes:
    """Builds an nmtrapd-formatted frame: version(1) + unused(1) + port(2) + addr(4) + length(4), all network order."""
    addr_int = int(ipaddress.IPv4Address(addr))
    return struct.pack("!BBHII", 0, 0, port, addr_int, len(pdu)) + pdu


@pytest.fixture(autouse=True)
def no_multiplexers_on_path(monkeypatch, tmp_path):
    """Keeps tests from starting any real straps or nmtrapd installed on the test machine."""
    monkeypatch.setenv("PATH", str(tmp_path / "empty-path"))


@pytest.fixture
def nonexistent_path(tmp_path):
    """Returns a path guaranteed not to exist on the filesystem.

    Unlike ``straps_socket_path``, this path is never used for an actual UNIX socket bind/connect,
    so the AF_UNIX 108-byte path length limit does not apply here.
    """
    path = tmp_path / "nonexistent"
    assert not path.exists()
    return str(path)


@pytest.fixture
def straps_socket_path(tmp_path_factory):
    """Returns a path for a test straps UNIX socket.

    Uses ``tmp_path_factory`` with a short name because AF_UNIX socket paths are limited to 108
    bytes on Linux, and pytest's default ``tmp_path`` combined with long test names can exceed
    this limit.
    """
    return str(tmp_path_factory.mktemp("straps") / "s.sock")


@pytest_asyncio.fixture
async def straps_unix_server(straps_socket_path):
    """Starts a mock straps UNIX socket server that sends a single framed trap."""
    frame = make_straps_frame("127.0.0.1", 162, SNMPV2C_COLDSTART_TRAP)
    stop = asyncio.Event()

    async def handle_client(reader, writer):
        writer.write(frame)
        await writer.drain()
        await stop.wait()
        writer.close()

    server = await asyncio.start_unix_server(handle_client, path=straps_socket_path)
    yield server
    stop.set()
    await asyncio.sleep(0)
    server.close()
    await server.wait_closed()


@pytest_asyncio.fixture
async def straps_receiver_with_localhost(straps_socket_path, state_with_localhost):
    config = TrapConfiguration(source="straps", straps_socket=straps_socket_path)
    receiver = StrapsTrapReceiver(trap_config=config, state=state_with_localhost)
    receiver.add_community("public")
    receiver.auto_subscribe_observers()
    return receiver
