import pytest
from pydantic import ValidationError

from zino.config import InvalidConfigurationError, read_configuration
from zino.config.models import EVENT_DUMP_DIR


class TestReadConfiguration:
    def test_returns_default_config_object_on_no_file(self):
        config = read_configuration()
        assert config
        assert config.archiving.old_events_dir == EVENT_DUMP_DIR

    def test_returns_config_defined_in_file(self, zino_non_default_conf, tmp_path):
        config = read_configuration(zino_non_default_conf)
        assert config
        assert config.polling.file == f"{tmp_path}/polldevs-empty.cf"

    def test_raises_error_on_file_not_found(self):
        with pytest.raises(OSError):
            read_configuration("non-existent-config.toml")

    def test_raises_error_on_invalid_toml_file(self, tmp_path):
        name = tmp_path / "invalid-config.toml"
        with open(name, "w") as conf:
            conf.write(
                """
                [archiving]
                old_events_dir = abc
                """
            )
        with pytest.raises(InvalidConfigurationError):
            read_configuration(name)

    def test_raises_error_on_invalid_config_values(self, tmp_path):
        name = tmp_path / "invalid-config-values.toml"
        with open(name, "w") as conf:
            conf.write(
                """
                [archiving]
                old_events_dir = false
                """
            )
        with pytest.raises(ValidationError):
            read_configuration(name)

    def tests_raises_error_on_misspelled_key(self, tmp_path):
        name = tmp_path / "extra-keys.toml"
        with open(name, "w") as conf:
            conf.write(
                """
                [archiving]
                typo = "old-zino-events"
                """
            )
        with pytest.raises(ValidationError):
            read_configuration(name)

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
