from datetime import datetime, timezone
import statistics

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.glucose import GlucoseReading
from app.utils.time import parse_window


def compute_tir(readings: list[int], low: int = 70, high: int = 180) -> float | None:
    if not readings:
        return None
    inside = sum(1 for g in readings if low <= g <= high)
    return inside / len(readings) * 100.0


def variability_label(readings: list[int]) -> str:
    if len(readings) < 10:
        return "unknown"
    mean = statistics.mean(readings)
    if mean <= 0:
        return "unknown"
    stdev = statistics.pstdev(readings)
    cv = stdev / mean
    if cv < 0.15:
        return "low"
    if cv < 0.30:
        return "medium"
    return "high"


def compute_gaps_hours(points_ts: list[datetime], expected_step_min: int = 5) -> float:
    if len(points_ts) < 2:
        return 0.0

    points_ts = sorted(points_ts)
    gap = 0.0
    for left, right in zip(points_ts, points_ts[1:]):
        dt_min = (right - left).total_seconds() / 60.0
        if dt_min > expected_step_min * 2:
            gap += max(0.0, dt_min - expected_step_min) / 60.0
    return round(gap, 2)


def get_glucose_points(db: Session, user_id: str, start: datetime, end: datetime) -> list[GlucoseReading]:
    stmt = (
        select(GlucoseReading)
        .where(
            GlucoseReading.user_id == user_id,
            GlucoseReading.ts >= start,
            GlucoseReading.ts < end,
        )
        .order_by(GlucoseReading.ts.asc())
    )
    return db.execute(stmt).scalars().all()


def get_glucose_summary(db: Session, user_id: str, window: str) -> dict:
    delta = parse_window(window)
    now = datetime.now(timezone.utc)
    start = now - delta

    rows = get_glucose_points(db, user_id, start, now)
    readings = [row.glucose_mgdl for row in rows]
    ts = [row.ts for row in rows]

    return {
        "window": window,
        "avg": round(sum(readings) / len(readings), 2) if readings else None,
        "min": min(readings) if readings else None,
        "max": max(readings) if readings else None,
        "tir_70_180_pct": round(compute_tir(readings), 2) if readings else None,
        "variability": variability_label(readings),
        "gaps_hours": compute_gaps_hours(ts),
    }
