from datetime import datetime, timedelta, timezone


def parse_window(window: str) -> timedelta:
    mapping = {
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }
    if window not in mapping:
        raise ValueError("invalid window")
    return mapping[window]


def today_utc_range(now: datetime | None = None) -> tuple[datetime, datetime]:
    now = now or datetime.now(timezone.utc)
    start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    return start, now
