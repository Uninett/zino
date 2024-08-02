import io

import pytest

from zino.config.models import PollDevice
from zino.config.polldevs import (
    InvalidConfiguration,
    _contains_defaults,
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
            default hcounters: yes

            name: example-gw
            """
        )
    yield name
