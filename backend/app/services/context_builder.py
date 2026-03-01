from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.meal import Meal
from app.models.symptom import Symptom
from app.models.feature import FeatureSnapshot
from app.models.user_profile import UserProfile
from app.services.glucose_service import get_glucose_summary


def build_user_context(db: Session, user_id: str) -> dict:
    now = datetime.now(timezone.utc)

    summary_24h = get_glucose_summary(db, user_id, "24h")
    summary_7d = get_glucose_summary(db, user_id, "7d")

    day_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    meals = db.execute(
        select(Meal)
        .where(Meal.user_id == user_id, Meal.meal_ts >= day_start, Meal.meal_ts < now)
        .order_by(Meal.meal_ts.asc())
    ).scalars().all()

    symptoms = db.execute(
        select(Symptom)
        .where(Symptom.user_id == user_id, Symptom.ts >= now - timedelta(days=7), Symptom.ts < now)
        .order_by(Symptom.ts.desc())
        .limit(20)
    ).scalars().all()

    kcal_today = sum(m.kcal for m in meals) if meals else 0

    return {
        "profile": {},
        "glucose_summary": {
            "last_24h": summary_24h,
            "last_7d": summary_7d,
        },
        "meals_today": [
            {
                "ts": meal.meal_ts.isoformat(),
                "kcal": meal.kcal,
                "tags": meal.tags,
                "source": meal.meal_ts_source.value,
                "photo_id": str(meal.photo_id) if meal.photo_id else None,
            }
            for meal in meals
        ],
        "symptoms_last_7d": [
            {
                "ts": s.ts.isoformat(),
                "severity": s.severity,
                "text": s.text,
            }
            for s in symptoms
        ],
        "data_quality": {
            "glucose_gaps_hours": summary_24h["gaps_hours"],
            "kcal_today": kcal_today,
        },
        "agent_features": _get_agent_features(db, user_id),
        "user_profile_info": _get_profile_info(db, user_id),
    }


def _get_agent_features(db: Session, user_id: str) -> dict:
    """Fetch latest feature snapshots for agent context."""
    result = {}
    for window in ("24h", "7d", "28d"):
        snap = db.execute(
            select(FeatureSnapshot)
            .where(FeatureSnapshot.user_id == user_id, FeatureSnapshot.window == window)
            .order_by(FeatureSnapshot.computed_at.desc())
            .limit(1)
        ).scalars().first()
        if snap:
            result[window] = snap.features
    return result


def _get_profile_info(db: Session, user_id: str) -> dict:
    """Fetch user profile info for agent context."""
    profile = db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    ).scalars().first()
    if not profile:
        return {}
    return {
        "subject_id": profile.subject_id,
        "cohort": profile.cohort,
        "liver_risk_level": profile.liver_risk_level,
    }
