import sys

import pytest

from zino.compat import StrEnum


@pytest.mark.skipif(sys.version_info >= (3, 11), reason="StrEnum compat is only valid for Python < 3.11")
def test_strenum_value_should_be_string():
    assert str(TestEnum.NOT_PRESENT) == "notPresent"


@pytest.mark.skipif(sys.version_info >= (3, 11), reason="StrEnum compat is only valid for Python < 3.11")
def test_strenum_should_be_able_to_instantiate_from_string():
    assert TestEnum("notPresent") == TestEnum.NOT_PRESENT


class TestEnum(StrEnum):
    UP = "up"
    DOWN = "down"
    NOT_PRESENT = "notPresent"
