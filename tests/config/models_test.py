import pydantic
import pytest

from zino.config.models import AgentConfiguration, PollDevice, SNMPConfiguration


class TestPollDevice:
    def test_init_should_fail_on_missing_address_or_name(self):
        with pytest.raises(pydantic.ValidationError):
            PollDevice()

    def test_init_should_succeed_with_address_and_name(self):
        assert PollDevice(name="example-gw", address="127.0.0.1")


class TestAgentConfiguration:
    def test_init_should_use_defaults(self):
        """Test that AgentConfiguration uses sensible defaults."""
        config = AgentConfiguration()
        assert config.enabled is True
        assert config.port == 8000
        assert config.address == "0.0.0.0"
        assert config.community == "public"

    def test_init_should_accept_custom_values(self):
        """Test that AgentConfiguration accepts custom values."""
        config = AgentConfiguration(
            enabled=False,
            port=8001,
            address="127.0.0.1",
            community="secret",
        )
        assert config.enabled is False
        assert config.port == 8001
        assert config.address == "127.0.0.1"
        assert config.community == "secret"

    def test_snmp_configuration_includes_agent(self):
        """Test that SNMPConfiguration includes agent configuration."""
        snmp_config = SNMPConfiguration()
        assert hasattr(snmp_config, "agent")
        assert isinstance(snmp_config.agent, AgentConfiguration)
        assert snmp_config.agent.enabled is True
        assert snmp_config.agent.port == 8000
