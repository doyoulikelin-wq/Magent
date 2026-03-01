from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id, get_db
from app.models.meal import Meal, MealPhoto
from app.services.glucose_service import get_glucose_summary

router = APIRouter()


@router.get("/health")
def dashboard_health(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    summary_24h = get_glucose_summary(db, user_id, "24h")
    summary_7d = get_glucose_summary(db, user_id, "7d")

    now = datetime.now(timezone.utc)
    day_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    meals_today = db.execute(
        select(Meal)
        .where(Meal.user_id == user_id, Meal.meal_ts >= day_start, Meal.meal_ts < now)
        .order_by(Meal.meal_ts.asc())
    ).scalars().all()

    return {
        "glucose": {
            "last_24h": summary_24h,
            "last_7d": summary_7d,
        },
        "kcal_today": sum(m.kcal for m in meals_today),
        "meals_today": [
            {
                "id": str(m.id),
                "ts": m.meal_ts,
                "kcal": m.kcal,
                "tags": m.tags,
                "source": m.meal_ts_source.value,
            }
            for m in meals_today
        ],
        "data_quality": {
            "glucose_gaps_hours": summary_24h["gaps_hours"],
            "variability": summary_24h["variability"],
        },
    }


@router.get("/meals")
def dashboard_meals(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    rows = db.execute(
        select(MealPhoto)
        .where(MealPhoto.user_id == user_id)
        .order_by(MealPhoto.uploaded_at.desc())
        .limit(50)
    ).scalars().all()

    return [
        {
            "id": str(photo.id),
            "uploaded_at": photo.uploaded_at,
            "status": photo.status.value,
            "calorie_estimate_kcal": photo.calorie_estimate_kcal,
            "confidence": photo.confidence,
            "vision_json": photo.vision_json,
        }
        for photo in rows
    ]


@router.get("/chat_threads")
def dashboard_chat_threads():
    return []
