"""Bound frontend polling after interrupted in-process background tasks."""
from datetime import datetime, timezone

MAX_JOB_SECONDS=180


def expired(row):
    created=row.created_at
    if created.tzinfo is None: created=created.replace(tzinfo=timezone.utc)
    return row.status in ('queued','running') and (datetime.now(timezone.utc)-created).total_seconds()>MAX_JOB_SECONDS
