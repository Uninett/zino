import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

from zino.config import InvalidConfigurationError, _resolve_model, format_validation_error, read_configuration


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
        with pytest.raises(FileNotFoundError):
            read_configuration(tmp_path / "non-existent-config.toml")

    def test_raises_error_on_invalid_toml_file(self, invalid_zino_conf):
        with pytest.raises(InvalidConfigurationError):
            read_configuration(invalid_zino_conf)

    def test_when_toml_is_invalid_then_error_should_carry_underlying_message(self, invalid_zino_conf):
        with pytest.raises(InvalidConfigurationError) as excinfo:
            read_configuration(invalid_zino_conf)

        # The underlying tomllib message names a line and column.
        message = str(excinfo.value)
        assert "line" in message
        assert "column" in message

    def test_raises_error_on_invalid_config_values(self, invalid_values_zino_conf):
        with pytest.raises(ValidationError) as excinfo:
            read_configuration(invalid_values_zino_conf)

        assert "archiving.old_events_dir" in str(excinfo)

    def tests_raises_error_on_misspelled_key(self, extra_keys_zino_conf):
        with pytest.raises(ValidationError) as excinfo:
            read_configuration(extra_keys_zino_conf)

        assert "Extra inputs are not permitted" in str(excinfo)

    def test_raises_error_on_pollfile_not_found(self, zino_conf_with_non_existent_pollfile):
        with pytest.raises(ValidationError) as excinfo:
            read_configuration(zino_conf_with_non_existent_pollfile)

        assert "polling.file" in str(excinfo.value)
        assert "non-existent-pollfile.cf doesn't exist or isn't readable" in str(excinfo.value)


class TestFormatValidationError:
    def test_when_key_is_misspelled_then_message_should_suggest_correct_key(self, extra_keys_zino_conf):
        with pytest.raises(ValidationError) as excinfo:
            read_configuration(extra_keys_zino_conf)

        messages = format_validation_error(excinfo.value)
        joined = "\n".join(messages)
        assert "Unknown configuration key" in joined
        assert "archiving.typo" in joined

    def test_when_section_is_misspelled_then_message_should_suggest_section(self, tmp_path):
        path = tmp_path / "section-typo.toml"
        path.write_text('[snmpp]\nbackend = "netsnmp"\n')
        with pytest.raises(ValidationError) as excinfo:
            read_configuration(path)

        messages = format_validation_error(excinfo.value)
        assert any("Unknown configuration key 'snmpp'" in m for m in messages)
        assert any("Did you mean 'snmp'" in m for m in messages)

    def test_when_literal_is_invalid_then_message_should_list_allowed_values(self, tmp_path):
        path = tmp_path / "bad-literal.toml"
        path.write_text('[snmp.trap]\nsource = "diirect"\n')
        with pytest.raises(ValidationError) as excinfo:
            read_configuration(path)

        messages = format_validation_error(excinfo.value)
        joined = "\n".join(messages)
        assert "snmp.trap.source" in joined
        assert "must be one of" in joined
        assert "'direct'" in joined and "'straps'" in joined and "'nmtrapd'" in joined

    def test_when_value_has_wrong_type_then_message_should_name_expected_type(self, tmp_path):
        path = tmp_path / "bad-type.toml"
        path.write_text('[persistence]\nperiod = "five"\n')
        with pytest.raises(ValidationError) as excinfo:
            read_configuration(path)

        messages = format_validation_error(excinfo.value)
        joined = "\n".join(messages)
        assert "persistence.period" in joined
        assert "must be of type int" in joined

    def test_when_pollfile_is_missing_then_message_should_describe_the_missing_file(
        self, zino_conf_with_non_existent_pollfile
    ):
        with pytest.raises(ValidationError) as excinfo:
            read_configuration(zino_conf_with_non_existent_pollfile)

        messages = format_validation_error(excinfo.value)
        assert any(
            m.startswith("Invalid value for 'polling.file':") and "doesn't exist or isn't readable" in m
            for m in messages
        )

    def test_when_required_field_is_missing_then_message_should_say_so(self):
        class Inner(BaseModel):
            model_config = ConfigDict(extra="forbid")

            required_field: str

        with pytest.raises(ValidationError) as excinfo:
            Inner.model_validate({})

        messages = format_validation_error(excinfo.value, model=Inner)
        assert messages == ["Missing required configuration key 'required_field'"]

    def test_when_loc_contains_a_list_index_then_message_should_render_brackets(self):
        class Inner(BaseModel):
            ports: list[int]

        with pytest.raises(ValidationError) as excinfo:
            Inner.model_validate({"ports": [10, "nope"]})

        messages = format_validation_error(excinfo.value, model=Inner)
        assert any("ports[1]" in m for m in messages)

    def test_when_unknown_key_is_inside_a_list_field_then_message_should_omit_suggestion(self):
        class Item(BaseModel):
            model_config = ConfigDict(extra="forbid")

            name: str

        class Root(BaseModel):
            model_config = ConfigDict(extra="forbid")

            items: list[Item]

        with pytest.raises(ValidationError) as excinfo:
            Root.model_validate({"items": [{"name": "ok", "extra": 1}]})

        messages = format_validation_error(excinfo.value, model=Root)
        assert messages == ["Unknown configuration key 'items[0].extra'"]


class TestResolveModel:
    def test_when_path_names_an_unknown_field_then_resolve_model_should_return_none(self):
        class Sub(BaseModel):
            x: int

        class Root(BaseModel):
            sub: Sub

        assert _resolve_model(Root, ("nonexistent",)) is None
