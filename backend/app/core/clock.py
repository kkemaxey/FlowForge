"""Single source of 'now' so business logic can be tested with a fixed time.

Times are stored as naive UTC with whole seconds: MySQL DATETIME rounds away
fractions, so trimming them here keeps API responses identical to stored rows.
"""
from datetime import UTC, datetime


def utc_now() -> datetime:
    """Current time as naive UTC, the form stored in the database."""
    return to_naive_utc(datetime.now(UTC))


def to_naive_utc(moment: datetime) -> datetime:
    """Normalize to naive UTC whole seconds; naive input is assumed to be UTC already."""
    if moment.tzinfo is not None:
        moment = moment.astimezone(UTC).replace(tzinfo=None)
    return moment.replace(microsecond=0)


def format_utc(moment: datetime) -> str:
    """Serialize a stored naive-UTC time as ISO 8601 with an explicit 'Z'."""
    return to_naive_utc(moment).isoformat() + "Z"
