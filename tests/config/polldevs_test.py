import io

import pytest

from zino.config.models import PollDevice
from zino.config.polldevs import (
    InvalidConfiguration,
    _contains_defaults,
    _normalize_keys,
    _parse_defaults,
    _read_conf_sections,
    read_polldevs,
)


class TestReadPolldevs:
    def test_should_generate_two_polldevices_from_test_config(self, polldevs_conf):
        result, _ = read_polldevs(polldevs_conf)
        assert len(result) == 2
        assert all(isinstance(device, PollDevice) for device in result.values())

    def test_should_return_default_values_from_test_config(self, polldevs_conf):
        _, defaults = read_polldevs(polldevs_conf)
        assert "community" in defaults
        assert defaults["community"] == "foobar"
        assert "domain" in defaults
        assert defaults["domain"] == "uninett.no"

    def test_should_use_default_values_in_polldevices_generated_from_test_config(self, polldevs_conf):
        result, _ = read_polldevs(polldevs_conf)
        assert all(device.community == "foobar" for device in result.values())
        assert all(device.domain == "uninett.no" for device in result.values())

    def test_when_hcounters_is_in_config_it_should_parse_correctly(self, polldevs_conf_with_hcounters):
        result, _ = read_polldevs(polldevs_conf_with_hcounters)
        assert len(result) == 2
        assert all(device.hcounters for device in result.values())


class TestReadInvalidPolldevs:
    def test_should_raise_exception(self, invalid_polldevs_conf):
        with pytest.raises(InvalidConfiguration):
            read_polldevs(invalid_polldevs_conf)

    def test_should_have_filename_in_exception(self, invalid_polldevs_conf):
        with pytest.raises(InvalidConfiguration) as e:
            read_polldevs(invalid_polldevs_conf)
        assert "polldevs.cf" in str(e.value)

    def test_should_have_line_number_in_exception(self, invalid_polldevs_conf):
        with pytest.raises(InvalidConfiguration) as e:
            read_polldevs(invalid_polldevs_conf)
        assert "2" in str(e.value)

    def test_exception_should_include_device_name_on_missing_address(self, missing_device_address_polldevs_conf):
        with pytest.raises(InvalidConfiguration) as e:
            read_polldevs(missing_device_address_polldevs_conf)
        assert "example-gw" in str(e.value)

    def test_exception_should_include_missing_attribute_on_missing_address(self, missing_device_address_polldevs_conf):
        with pytest.raises(InvalidConfiguration) as e:
            read_polldevs(missing_device_address_polldevs_conf)
        assert "Field required ('address')" in str(e.value)


class TestReadConfSections:
    def test_when_file_is_empty_it_should_return_nothing(self):
        data = io.StringIO("")
        result = list(_read_conf_sections(data))
        assert not result

    def test_when_file_contains_two_sections_it_should_yield_two_dicts(self):
        data = io.StringIO(
            """
            name: zaphod

            name: ford
            """
        )
        result = list(_read_conf_sections(data))
        assert len(result) == 2
        assert all(isinstance(block, dict) for lineno, block in result)

    def test_when_file_contains_comments_they_should_be_ignored(self):
        data = io.StringIO(
            """
            # comment: just a comment
            name: zaphod
            #address: 192.168.0.1
            address: 127.0.0.1
            """
        )
        expected = {"name": "zaphod", "address": "127.0.0.1"}
        result = list(block for lineno, block in _read_conf_sections(data))
        assert result == [expected]

    def test_when_file_contains_non_assignments_it_should_fail(self):
        data = io.StringIO(
            """
            random data
            not a config file
            """
        )
        with pytest.raises(InvalidConfiguration):
            list(_read_conf_sections(data))


class TestContainsDefaults:
    def test_when_section_contains_at_least_one_default_key_it_should_return_true(self):
        section = {"default value": "foobar", "other": "cromulent"}
        assert _contains_defaults(section)

    def test_when_section_contains_no_default_keys_it_should_return_false(self):
        section = {"value 1": "foobar", "value 2": "cromulent"}
        assert not _contains_defaults(section)


class TestParseDefaults:
    def test_all_default_values_should_be_returned(self):
        section = {"default value1": "foobar", "default value2": "cromulent", "value3": "zaphod"}
        expected = {"value1": "foobar", "value2": "cromulent"}
        assert _parse_defaults(section) == expected

    def test_hyphenated_keys_should_be_normalized_to_underscores(self):
        section = {"default max-repetitions": "5", "default do-bgp": "yes"}
        result = _parse_defaults(section)
        assert "max_repetitions" in result
        assert "do_bgp" in result


class TestNormalizeKeys:
    def test_should_replace_hyphens_with_underscores(self):
        section = {"max-repetitions": "5", "do-bgp": "yes", "name": "test"}
        expected = {"max_repetitions": "5", "do_bgp": "yes", "name": "test"}
        assert _normalize_keys(section) == expected

    def test_should_handle_empty_dict(self):
        assert _normalize_keys({}) == {}

    def test_should_preserve_keys_without_hyphens(self):
        section = {"name": "test", "address": "192.168.1.1"}
        assert _normalize_keys(section) == section


@pytest.fixture
def missing_device_address_polldevs_conf(tmp_path):
    name = tmp_path.joinpath("polldevs.cf")
    with open(name, "w") as conf:
        conf.write(
            """# polldevs test config
            default interval: 5
            default community: foobar
            default domain: uninett.no
            default statistics: yes
            default snmpversion: v2c

            name: example-gw
            """
        )
    yield name


@pytest.fixture
def polldevs_conf_with_hcounters(tmp_path):
    name = tmp_path.joinpath("polldevs.cf")
    with open(name, "w") as conf:
        conf.write(
            """# polldevs test config
            default interval: 5
            default community: foobar
            default domain: uninett.no
            default statistics: yes
            default snmpversion: v2c
            default hcounters: yes

            name: example-gw
            address: 10.0.42.1
            hcounters: yes

            name: example-gw2
            address: 10.0.43.1
            """
        )
    yield name


@pytest.fixture
def polldevs_conf_with_max_repetitions(tmp_path):
    name = tmp_path.joinpath("polldevs.cf")
    with open(name, "w") as conf:
        conf.write(
            """# polldevs test config
            default interval: 5
            default community: foobar
            default domain: uninett.no
            default snmpversion: v2c
            default max-repetitions: 5

            name: example-gw
            address: 10.0.42.1

            name: example-gw2
            address: 10.0.43.1
            max-repetitions: 3
            """
        )
    yield name


class TestMaxRepetitions:
    def test_should_read_global_default_max_repetitions(self, polldevs_conf_with_max_repetitions):
        result, defaults = read_polldevs(polldevs_conf_with_max_repetitions)
        assert "max_repetitions" in defaults
        assert defaults["max_repetitions"] == "5"

    def test_should_use_global_default_max_repetitions_in_device(self, polldevs_conf_with_max_repetitions):
        result, _ = read_polldevs(polldevs_conf_with_max_repetitions)
        assert result["example-gw"].max_repetitions == 5

    def test_device_override_should_take_precedence_over_global_default(self, polldevs_conf_with_max_repetitions):
        result, _ = read_polldevs(polldevs_conf_with_max_repetitions)
        assert result["example-gw2"].max_repetitions == 3

    def test_when_max_repetitions_not_specified_should_be_none(self, polldevs_conf):
        result, _ = read_polldevs(polldevs_conf)
        assert all(device.max_repetitions is None for device in result.values())

    def test_invalid_max_repetitions_should_raise_exception(self, polldevs_conf_with_invalid_max_repetitions):
        with pytest.raises(InvalidConfiguration) as exc_info:
            read_polldevs(polldevs_conf_with_invalid_max_repetitions)
        assert "max_repetitions" in str(exc_info.value)


@pytest.fixture
def polldevs_conf_with_invalid_max_repetitions(tmp_path):
    name = tmp_path.joinpath("polldevs.cf")
    with open(name, "w") as conf:
        conf.write(
            """# polldevs test config
            name: example-gw
            address: 10.0.42.1
            max-repetitions: 0
            """
        )
    yield name
