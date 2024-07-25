import pytest
from pydantic import ValidationError

from zino.config import InvalidConfigurationError, read_configuration


class TestReadConfiguration:
    def test_returns_config_defined_in_file(self, zino_conf, polldevs_conf_with_no_routers):
        config = read_configuration(zino_conf)
        assert config
        assert config.polling.file == str(polldevs_conf_with_no_routers)

    def test_pollfile_argument_overrides_pollfile_defined_in_file(self, zino_conf, polldevs_conf_with_single_router):
        config = read_configuration(config_file_name=zino_conf, poll_file_name=str(polldevs_conf_with_single_router))
        assert config
        assert config.polling.file == str(polldevs_conf_with_single_router)

    def test_raises_error_on_file_not_found(self, tmp_path):
        with pytest.raises(OSError):
            read_configuration(tmp_path / "non-existent-config.toml")

    def test_raises_error_on_invalid_toml_file(self, invalid_zino_conf):
        with pytest.raises(InvalidConfigurationError):
            read_configuration(invalid_zino_conf)

    def test_raises_error_on_invalid_config_values(self, invalid_values_zino_conf):
        with pytest.raises(ValidationError):
            read_configuration(invalid_values_zino_conf)

    def tests_raises_error_on_misspelled_key(self, extra_keys_zino_conf):
        with pytest.raises(ValidationError):
            read_configuration(extra_keys_zino_conf)

    def test_raises_error_on_pollfile_not_found(self, zino_conf_with_non_existent_pollfile):
        with pytest.raises(ValidationError):
            read_configuration(zino_conf_with_non_existent_pollfile)
