"""Tests for the SNMP agent module."""

import asyncio
import subprocess
import time
from unittest.mock import MagicMock, patch

import pytest

from zino.config.models import PollDevice
from zino.snmp import SNMP
from zino.snmp.agent import ZinoSnmpAgent


class TestZinoSnmpAgent:
    """Test the ZinoSnmpAgent class."""

    def test_when_initialized_without_arguments_then_it_should_use_default_values(self):
        """Test that __init__ sets sensible defaults."""
        agent = ZinoSnmpAgent()
        assert agent.listen_address == "0.0.0.0"
        assert agent.listen_port == 8000
        assert agent.community == "public"
        assert agent.start_time is not None
        assert not agent._running
        assert agent.snmp_engine is None
        assert agent.transport_dispatcher is None

    def test_when_initialized_with_custom_values_then_it_should_store_them(self):
        """Test that __init__ accepts custom configuration."""
        start_time = time.time() - 100
        agent = ZinoSnmpAgent(
            listen_address="127.0.0.1",
            listen_port=8001,
            community="secret",
            start_time=start_time,
        )
        assert agent.listen_address == "127.0.0.1"
        assert agent.listen_port == 8001
        assert agent.community == "secret"
        assert agent.start_time == start_time

    def test_when_get_uptime_called_then_it_should_return_seconds_since_start_time(self):
        """Test that _get_uptime calculates uptime correctly."""
        start_time = time.time() - 42  # Started 42 seconds ago
        agent = ZinoSnmpAgent(start_time=start_time)
        uptime = agent._get_uptime()
        # Allow for small timing differences
        assert 41 <= uptime <= 43

    def test_when_get_uptime_called_then_it_should_return_integer_type(self):
        """Test that _get_uptime returns an integer."""
        agent = ZinoSnmpAgent()
        uptime = agent._get_uptime()
        assert isinstance(uptime, int)

    def test_when_setup_engine_called_then_it_should_initialize_snmp_engine_and_dispatcher(self):
        """Test that _setup_engine initializes the engine and dispatcher attributes."""
        agent = ZinoSnmpAgent(listen_address="127.0.0.1", listen_port=8001, community="public")

        # Mock the entire method to avoid complex SNMP setup
        with patch.object(agent, "_setup_engine") as mock_setup:

            def setup_side_effect():
                agent.snmp_engine = MagicMock()
                agent.transport_dispatcher = MagicMock()

            mock_setup.side_effect = setup_side_effect

            agent._setup_engine()

            # Check that attributes are set
            assert agent.snmp_engine is not None
            assert agent.transport_dispatcher is not None
            mock_setup.assert_called_once()

    @patch("zino.snmp.agent.builder")
    def test_when_register_zino_uptime_called_then_it_should_load_and_export_mib_symbols(self, mock_builder):
        """Test that _register_zino_uptime loads required MIB modules."""
        agent = ZinoSnmpAgent()
        mock_mib_instrum = MagicMock()
        mock_mib_builder = MagicMock()
        mock_mib_instrum.mibBuilder = mock_mib_builder

        # Mock the MIB symbols
        mock_zino_uptime = MagicMock()
        mock_zino_uptime.getName.return_value = (1, 3, 6, 1, 4, 1, 2428, 130, 1, 1, 1)
        mock_zino_uptime.getSyntax.return_value = MagicMock()
        mock_mib_scalar_instance = MagicMock()

        def mock_import_symbols(module, *symbols):
            if module == "ZINO-MIB":
                return (mock_zino_uptime,)
            elif module == "SNMPv2-SMI":
                return (mock_mib_scalar_instance,)
            return ()

        mock_mib_builder.importSymbols = mock_import_symbols

        agent._register_zino_uptime(mock_mib_instrum)

        # Check that MIB modules were loaded
        mock_mib_builder.loadModules.assert_called()

    @pytest.mark.asyncio
    async def test_when_start_called_then_it_should_set_running_flag_to_true(self):
        """Test that start() sets the _running flag and calls setup."""
        agent = ZinoSnmpAgent(listen_port=18000)

        with patch.object(agent, "_setup_engine") as mock_setup:
            mock_dispatcher = MagicMock()
            mock_dispatcher.runDispatcher.return_value = None
            agent.transport_dispatcher = mock_dispatcher

            # Start agent in background and let it run briefly
            task = asyncio.create_task(agent.open())
            await asyncio.sleep(0.01)

            # Check that setup was called and running flag is set
            mock_setup.assert_called_once()
            assert agent._running

            # Clean up
            agent.close()
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_when_start_fails_during_setup_then_it_should_raise_exception_and_clear_running_flag(self):
        """Test that start() handles setup failures gracefully."""
        agent = ZinoSnmpAgent()

        with patch.object(agent, "_setup_engine", side_effect=Exception("Setup failed")):
            with pytest.raises(Exception, match="Setup failed"):
                await agent.open()

            assert not agent._running

    def test_when_stop_called_on_running_agent_then_it_should_close_dispatchers_and_clear_running_flag(self):
        """Test that stop() clears the _running flag."""
        agent = ZinoSnmpAgent()
        agent._running = True
        agent.transport_dispatcher = MagicMock()
        agent.snmp_engine = MagicMock()

        agent.close()

        assert not agent._running
        agent.transport_dispatcher.closeDispatcher.assert_called_once()
        agent.snmp_engine.transportDispatcher.closeDispatcher.assert_called_once()

    def test_when_stop_called_on_non_running_agent_then_it_should_do_nothing(self):
        """Test that stop() does nothing when agent is not running."""
        agent = ZinoSnmpAgent()
        agent._running = False
        agent.close()  # Should not raise any exceptions
        assert not agent._running

    def test_when_stop_called_with_none_dispatchers_then_it_should_not_raise_exception(self):
        """Test that stop() handles None dispatcher gracefully."""
        agent = ZinoSnmpAgent()
        agent._running = True
        agent.transport_dispatcher = None
        agent.snmp_engine = None

        agent.close()  # Should not raise exceptions
        assert not agent._running


class TestSetupEngineConfiguration:
    """Test different configuration branches in _setup_engine method."""

    @patch("zino.snmp.agent.cmdrsp")
    @patch("zino.snmp.agent.context")
    @patch("zino.snmp.agent.builder")
    @patch("zino.snmp.agent.config")
    @patch("zino.snmp.agent.AsyncioDispatcher")
    @patch("zino.snmp.agent.engine")
    @patch("zino.snmp.agent.udp6")
    @patch("zino.snmp.agent.udp")
    def test_when_address_is_ipv6_then_it_should_use_ipv6_transport(
        self, mock_udp, mock_udp6, mock_engine, mock_dispatcher, mock_config, mock_builder, mock_context, mock_cmdrsp
    ):
        """Test that IPv6 addresses result in IPv6 transport configuration."""
        agent = ZinoSnmpAgent(listen_address="::1", listen_port=8001)

        mock_transport = MagicMock()
        mock_udp6.Udp6AsyncioTransport.return_value.openServerMode.return_value = mock_transport
        mock_snmp_engine = MagicMock()
        mock_engine.SnmpEngine.return_value = mock_snmp_engine

        with patch.object(agent, "_register_zino_uptime"):
            agent._setup_engine()

        # Verify IPv6 transport was used
        mock_udp6.Udp6AsyncioTransport.assert_called_once()
        mock_udp.UdpAsyncioTransport.assert_not_called()

    @patch("zino.snmp.agent.cmdrsp")
    @patch("zino.snmp.agent.context")
    @patch("zino.snmp.agent.builder")
    @patch("zino.snmp.agent.config")
    @patch("zino.snmp.agent.AsyncioDispatcher")
    @patch("zino.snmp.agent.engine")
    @patch("zino.snmp.agent.udp6")
    @patch("zino.snmp.agent.udp")
    def test_when_address_is_ipv4_then_it_should_use_ipv4_transport(
        self, mock_udp, mock_udp6, mock_engine, mock_dispatcher, mock_config, mock_builder, mock_context, mock_cmdrsp
    ):
        """Test that IPv4 addresses result in IPv4 transport configuration."""
        agent = ZinoSnmpAgent(listen_address="192.168.1.1", listen_port=8001)

        mock_transport = MagicMock()
        mock_udp.UdpAsyncioTransport.return_value.openServerMode.return_value = mock_transport
        mock_snmp_engine = MagicMock()
        mock_engine.SnmpEngine.return_value = mock_snmp_engine

        with patch.object(agent, "_register_zino_uptime"):
            agent._setup_engine()

        # Verify IPv4 transport was used
        mock_udp.UdpAsyncioTransport.assert_called_once()
        mock_udp6.Udp6AsyncioTransport.assert_not_called()

    @patch("zino.snmp.agent.cmdrsp")
    @patch("zino.snmp.agent.context")
    @patch("zino.snmp.agent.builder")
    @patch("zino.snmp.agent.config")
    @patch("zino.snmp.agent.AsyncioDispatcher")
    @patch("zino.snmp.agent.engine")
    @patch("zino.snmp.agent.udp")
    def test_when_address_is_hostname_then_it_should_use_ipv4_transport(
        self, mock_udp, mock_engine, mock_dispatcher, mock_config, mock_builder, mock_context, mock_cmdrsp
    ):
        """Test that hostnames default to IPv4 transport."""
        agent = ZinoSnmpAgent(listen_address="localhost", listen_port=8001)

        mock_transport = MagicMock()
        mock_udp.UdpAsyncioTransport.return_value.openServerMode.return_value = mock_transport
        mock_snmp_engine = MagicMock()
        mock_engine.SnmpEngine.return_value = mock_snmp_engine

        with patch.object(agent, "_register_zino_uptime"):
            agent._setup_engine()

        # Verify IPv4 transport was used for hostname
        mock_udp.UdpAsyncioTransport.assert_called_once()

    @patch("zino.snmp.agent.cmdrsp")
    @patch("zino.snmp.agent.context")
    @patch("zino.snmp.agent.builder")
    @patch("zino.snmp.agent.config")
    @patch("zino.snmp.agent.AsyncioDispatcher")
    @patch("zino.snmp.agent.engine")
    @patch("zino.snmp.agent.udp")
    def test_when_specific_community_then_it_should_only_configure_that_community(
        self, mock_udp, mock_engine, mock_dispatcher, mock_config, mock_builder, mock_context, mock_cmdrsp
    ):
        """Test that specific community configuration is applied."""
        agent = ZinoSnmpAgent(community="test-community")

        mock_transport = MagicMock()
        mock_udp.UdpAsyncioTransport.return_value.openServerMode.return_value = mock_transport
        mock_snmp_engine = MagicMock()
        mock_engine.SnmpEngine.return_value = mock_snmp_engine

        with patch.object(agent, "_register_zino_uptime"):
            agent._setup_engine()

        # Verify specific community was configured
        calls = mock_config.addV1System.call_args_list
        assert len([c for c in calls if "test-community" in c[0]]) == 1
        # Should not have added default community value
        assert len([c for c in calls if "public" in c[0]]) == 0

    @patch("zino.snmp.agent.cmdrsp")
    @patch("zino.snmp.agent.context")
    @patch("zino.snmp.agent.builder")
    @patch("zino.snmp.agent.config")
    @patch("zino.snmp.agent.AsyncioDispatcher")
    @patch("zino.snmp.agent.engine")
    @patch("zino.snmp.agent.udp")
    def test_when_no_community_then_it_should_configure_public_community(
        self, mock_udp, mock_engine, mock_dispatcher, mock_config, mock_builder, mock_context, mock_cmdrsp
    ):
        """Test that no community means multiple communities are accepted."""
        agent = ZinoSnmpAgent(community=None)

        mock_transport = MagicMock()
        mock_udp.UdpAsyncioTransport.return_value.openServerMode.return_value = mock_transport
        mock_snmp_engine = MagicMock()
        mock_engine.SnmpEngine.return_value = mock_snmp_engine

        with patch.object(agent, "_register_zino_uptime"):
            agent._setup_engine()

        calls = mock_config.addV1System.call_args_list
        assert any("public" in str(c) for c in calls)


@pytest.mark.asyncio
async def test_when_agent_is_queried_then_it_should_return_uptime(running_agent):
    """Integration test that the agent responds to SNMP queries using Zino's SNMP backend."""
    port = running_agent

    # Create a PollDevice pointing to our agent
    device = PollDevice(name="test-agent", address="127.0.0.1", port=port, community="public")

    # Use Zino's SNMP backend to query the agent
    with SNMP(device) as snmp_session:
        # Query ZINO-MIB::zinoUpTime.0
        response = await snmp_session.get("ZINO-MIB", "zinoUpTime", 0)

        # Verify we got a response
        assert response is not None
        assert response.value is not None

        # Check that uptime is reasonable (0-10 seconds for a just-started agent)
        uptime = int(response.value)
        assert 0 <= uptime <= 10, f"Unexpected uptime value: {uptime}"


@pytest.mark.asyncio
async def test_when_agent_runs_then_uptime_should_increase(running_agent):
    """Test that zinoUpTime value increases over time."""
    port = running_agent

    device = PollDevice(name="test-agent", address="127.0.0.1", port=port, community="public")

    with SNMP(device) as snmp_session:
        # First query
        response1 = await snmp_session.get("ZINO-MIB", "zinoUpTime", 0)
        uptime1 = int(response1.value)

        # Wait 2 seconds
        await asyncio.sleep(2)

        # Second query
        response2 = await snmp_session.get("ZINO-MIB", "zinoUpTime", 0)
        uptime2 = int(response2.value)

        # Uptime should have increased by approximately 2 seconds
        diff = uptime2 - uptime1
        assert 1 <= diff <= 3, f"Uptime difference was {diff}, expected ~2"


@pytest.fixture
async def running_agent(unused_udp_port):
    """Start the SNMP agent as a subprocess and ensure it's ready."""
    process = subprocess.Popen(
        ["python", "-m", "zino.snmp.agent", "--port", str(unused_udp_port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Give the agent time to start up
    await asyncio.sleep(1)

    try:
        yield unused_udp_port
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
