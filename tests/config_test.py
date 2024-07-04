import pytest
from pydantic import ValidationError

from zino.config import InvalidConfigurationError, read_configuration


class TestReadConfiguration:
    def test_returns_config_defined_in_file(self, zino_conf, tmp_path):
        config = read_configuration(zino_conf)
        assert config
        assert config.polling.file == f"{tmp_path}/polldevs-empty.cf"

    def test_raises_error_on_file_not_found(self):
        with pytest.raises(OSError):
            read_configuration("non-existent-config.toml")

    def test_raises_error_on_invalid_toml_file(self, invalid_zino_conf):
        with pytest.raises(InvalidConfigurationError):
            read_configuration(invalid_zino_conf)

    def test_raises_error_on_invalid_config_values(self, invalid_values_zino_conf):
        with pytest.raises(ValidationError):
            read_configuration(invalid_values_zino_conf)

    def tests_raises_error_on_misspelled_key(self, extra_keys_zino_conf):
        with pytest.raises(ValidationError):
            read_configuration(extra_keys_zino_conf)

    def test_raises_error_on_pollfile_not_found(self, tmp_path):
        name = tmp_path / "non-existent-pollfile.toml"
        with open(name, "w") as conf:
            conf.write(
                """
                [polling]
                file = "non-existent-pollfile.cf"
                """
            )
        with pytest.raises(ValidationError):
            read_configuration(name)
