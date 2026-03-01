from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.services.glucose_service import get_glucose_points


def infer_meal_time_from_glucose(db: Session, user_id: str, uploaded_at: datetime) -> tuple[datetime | None, float]:
    """Infer meal time around upload window using a simple slope/rise score."""
    start = uploaded_at - timedelta(hours=2)
    end = uploaded_at + timedelta(hours=2)

    rows = get_glucose_points(db, user_id, start, end)
    if len(rows) < 10:
        return None, 0.0

    best_ts = None
    best_score = 0.0

    for i in range(3, len(rows)):
        current = rows[i]
        prev = rows[i - 3]

        dt_min = (current.ts - prev.ts).total_seconds() / 60.0
        if dt_min <= 0:
            continue

        slope = (current.glucose_mgdl - prev.glucose_mgdl) / dt_min
        rise = current.glucose_mgdl - prev.glucose_mgdl
        score = max(0.0, slope) * max(0.0, rise)

        if score > best_score:
            best_score = score
            best_ts = rows[i - 1].ts

    if best_ts is None:
        return None, 0.0

    confidence = min(1.0, best_score / 200.0)
    return best_ts, round(confidence, 2)
