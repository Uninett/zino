# mypy: ignore-errors
"""Compatibility layer for older versions of Python"""

try:
    from enum import StrEnum
except ImportError:
    # < Python 3.11
    from enum import Enum

    class StrEnum(str, Enum):
        __str__ = str.__str__

        def _generate_next_value_(name, start, count, last_values):
            """
            Return the lower-cased version of the member name.
            """
            return name.lower()


__all__ = ["StrEnum"]
