"""Zino time related functions"""

from datetime import UTC, datetime


def now() -> datetime:
    """Returns current time as UTC time with timezone information"""
    return datetime.now(UTC)
