"""Zino time related functions"""

from datetime import datetime, timezone


def now() -> datetime:
    """Returns current time as UTC time with timezone information"""
    return datetime.now(timezone.utc)
