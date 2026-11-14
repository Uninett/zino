from copy import deepcopy

import pydantic
import pytest

from zino.config.models import (
    DEFAULT_LOGGING_CONFIG,
    AgentConfiguration,
    Configuration,
    PollDevice,
    ProcessConfiguration,
    SNMPBackendConfiguration,
    SNMPConfiguration,
    TrapConfiguration,
)


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


class TestConfiguration:
    def test_when_instance_logging_is_changed_then_default_logging_config_should_be_unchanged(self):
        original = deepcopy(DEFAULT_LOGGING_CONFIG)
        config = Configuration()

        config.logging["loggers"]["vwatcher"] = {"level": "DEBUG"}

        assert DEFAULT_LOGGING_CONFIG == original


class TestSNMPBackendConfiguration:
    def test_when_backend_is_omitted_then_default_should_be_netsnmp(self):
        assert SNMPBackendConfiguration().backend == "netsnmp"

    def test_when_trap_section_is_given_then_it_should_be_rejected(self):
        with pytest.raises(pydantic.ValidationError):
            SNMPBackendConfiguration.model_validate({"trap": {"source": "direct"}})


class TestSNMPConfiguration:
    def test_when_backend_is_omitted_then_default_should_be_netsnmp(self):
        """vwatcher relies on this default, even though it is inherited from SNMPBackendConfiguration"""
        assert SNMPConfiguration().backend == "netsnmp"

    def test_when_unknown_key_is_given_then_it_should_be_rejected(self):
        with pytest.raises(pydantic.ValidationError):
            SNMPConfiguration.model_validate({"bakcend": "pysnmp"})


class TestTrapConfiguration:
    def test_when_source_is_omitted_then_default_should_be_direct(self):
        config = TrapConfiguration()
        assert config.source == "direct"

    def test_when_source_is_straps_then_config_should_accept_it(self):
        config = TrapConfiguration(source="straps")
        assert config.source == "straps"

    def test_when_source_is_nmtrapd_then_config_should_accept_it(self):
        config = TrapConfiguration(source="nmtrapd")
        assert config.source == "nmtrapd"

    def test_when_straps_socket_is_set_then_config_should_store_it(self):
        config = TrapConfiguration(source="straps", straps_socket="/var/run/straps.sock")
        assert config.straps_socket == "/var/run/straps.sock"

    def test_when_source_is_invalid_then_it_should_raise_validation_error(self):
        with pytest.raises(pydantic.ValidationError):
            TrapConfiguration(source="bogus")

    def test_when_start_multiplexer_is_omitted_then_it_should_default_to_true(self):
        config = TrapConfiguration(source="straps")
        assert config.start_multiplexer is True

    def test_when_multiplexer_command_is_omitted_then_it_should_default_to_none(self):
        config = TrapConfiguration(source="straps")
        assert config.multiplexer_command is None

    def test_when_multiplexer_command_is_set_then_config_should_store_it(self):
        config = TrapConfiguration(source="straps", multiplexer_command=["/usr/pkg/bin/straps", "162"])
        assert config.multiplexer_command == ["/usr/pkg/bin/straps", "162"]

    def test_when_multiplexer_command_is_empty_then_it_should_raise_validation_error(self):
        with pytest.raises(pydantic.ValidationError):
            TrapConfiguration(source="straps", multiplexer_command=[])


class TestProcessConfiguration:
    def test_init_should_use_defaults(self):
        """Test that ProcessConfiguration uses sensible defaults."""
        config = ProcessConfiguration()
        assert config.user is None

    def test_init_should_accept_user(self):
        """Test that ProcessConfiguration accepts a user value."""
        config = ProcessConfiguration(user="zino")
        assert config.user == "zino"

    def test_configuration_includes_process(self):
        """Test that Configuration includes process configuration."""
        config = Configuration()
        assert hasattr(config, "process")
        assert isinstance(config.process, ProcessConfiguration)
        assert config.process.user is None
