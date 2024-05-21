from zino.config.models import PollDevice
from zino.config.polldevs import _contains_defaults, _parse_defaults, read_polldevs


class TestReadPolldevs:
    def test_should_generate_two_polldevices_from_test_config(self, polldevs_conf):
        result = list(read_polldevs(polldevs_conf))
        assert len(result) == 2
        assert all(isinstance(device, PollDevice) for device in result)

    def test_should_use_default_values_in_polldevices_generated_from_test_config(self, polldevs_conf):
        result = list(read_polldevs(polldevs_conf))
        assert all(device.community == "foobar" for device in result)
        assert all(device.domain == "uninett.no" for device in result)


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
