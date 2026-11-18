from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

TZ_HOURS = 3  # توقيت مكة/الرياض


def _local(now: float) -> datetime:
    return datetime.fromtimestamp(now, timezone.utc) + timedelta(hours=TZ_HOURS)


def day_start(now: float | None = None) -> float:
    n = _local(now if now is not None else time.time())
    start = n.replace(hour=0, minute=0, second=0, microsecond=0)
    return (start - timedelta(hours=TZ_HOURS)).timestamp()


def week_start(now: float | None = None) -> float:
    """بداية الأسبوع: الأحد 00:00 بتوقيت مكة."""
    n = _local(now if now is not None else time.time())
    days = (n.weekday() + 1) % 7          # الأحد = 0
    start = (n - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
    return (start - timedelta(hours=TZ_HOURS)).timestamp()
