"""Pydantic types shared by every module's request/response schemas."""
from datetime import datetime, timezone
from typing import Annotated

from pydantic import AfterValidator, PlainSerializer


def _to_utc_ms(value: datetime) -> datetime:
    """Store as naive UTC, cut to milliseconds (DATETIME(3)). Naive input is taken as UTC."""
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value.replace(microsecond=value.microsecond // 1000 * 1000)


def _iso_ms_z(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%S.") + f"{value.microsecond // 1000:03d}Z"


# UTC timestamp, read from any ISO 8601 input and written as "2026-10-20T14:02:11.204Z".
UtcDatetime = Annotated[datetime, AfterValidator(_to_utc_ms), PlainSerializer(_iso_ms_z, return_type=str)]
