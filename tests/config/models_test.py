import pydantic
import pytest

from zino.config.models import PollDevice


class TestPollDevice:
    def test_init_should_fail_on_missing_address_or_name(self):
        with pytest.raises(pydantic.ValidationError):
            PollDevice()

    def test_init_should_succeed_with_address_and_name(self):
        assert PollDevice(name="example-gw", address="127.0.0.1")
