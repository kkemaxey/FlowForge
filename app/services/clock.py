from datetime import datetime, timezone


def utc_now() -> datetime:
    """Current UTC time without tzinfo, matching how MySQL DATETIME stores it."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
