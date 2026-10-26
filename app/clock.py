"""UTC helpers.

SQLite has no native timezone support, so datetimes are stored as naive UTC
values and only given an explicit offset when they leave the API.
"""

from datetime import UTC, datetime
from typing import overload


def utcnow() -> datetime:
    """Current time as naive UTC, matching the storage convention."""
    return datetime.now(UTC).replace(tzinfo=None)


@overload
def as_utc(value: datetime) -> datetime: ...


@overload
def as_utc(value: None) -> None: ...


def as_utc(value: datetime | None) -> datetime | None:
    """Attach a UTC offset to a stored (naive) datetime."""
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=UTC)
