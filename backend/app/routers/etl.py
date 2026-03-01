"""ETL and Feature Store API endpoints.

These endpoints are intended for admin / batch operations, not end-user use.
Authentication is intentionally relaxed for the MVP demo.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_db
from app.models.feature import FeatureSnapshot
from app.models.user_profile import UserProfile
from app.schemas.etl import ETLRunResponse, FeatureSnapshotOut
from app.services.etl.feature_compute import compute_all_features, compute_features_for_user
from app.services.etl.glucose_etl import run_glucose_etl
from app.services.etl.meal_etl import import_activity_food, import_corrected_meals

logger = logging.getLogger(__name__)

router = APIRouter()

# Default data directory – can be overridden via env
DATA_DIR = Path(getattr(settings, "DATA_DIR", "/app/data"))


# ---------------------------------------------------------------------------
# Batch ETL
# ---------------------------------------------------------------------------


@router.post("/run-batch", response_model=ETLRunResponse, summary="Run full batch ETL pipeline")
def run_batch_etl(
    data_dir: str | None = Query(default=None, description="Override data directory path"),
    skip_glucose: bool = Query(default=False),
    skip_meals: bool = Query(default=False),
    skip_features: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> ETLRunResponse:
    """Execute the full ETL pipeline: glucose → meals → features."""
    target_dir = Path(data_dir) if data_dir else DATA_DIR
    errors: list[str] = []
    result = ETLRunResponse()

    # 1. Glucose ETL
    if not skip_glucose:
        try:
            result.glucose = run_glucose_etl(db, target_dir)
        except Exception as exc:
            logger.exception("Glucose ETL failed")
            errors.append(f"glucose: {exc}")

    # 2. Meals ETL (raw)
    if not skip_meals:
        try:
            result.meals_raw = import_activity_food(db, target_dir)
        except Exception as exc:
            logger.exception("Meal (raw) ETL failed")
            errors.append(f"meals_raw: {exc}")

        # 3. Meals ETL (corrected)
        try:
            result.meals_corrected = import_corrected_meals(db, target_dir)
        except Exception as exc:
            logger.exception("Meal (corrected) ETL failed")
            errors.append(f"meals_corrected: {exc}")

    # 4. Feature computation
    if not skip_features:
        try:
            result.features = compute_all_features(db)
        except Exception as exc:
            logger.exception("Feature computation failed")
            errors.append(f"features: {exc}")

    result.errors = errors if errors else None
    result.status = "ok" if not errors else "partial"
    return result


# ---------------------------------------------------------------------------
# Feature queries
# ---------------------------------------------------------------------------


@router.get("/features/{subject_id}", response_model=list[FeatureSnapshotOut])
def get_features(
    subject_id: str,
    window: str | None = Query(default=None, description="Filter by window: 24h, 7d, 28d"),
    db: Session = Depends(get_db),
) -> list[FeatureSnapshotOut]:
    """Retrieve latest feature snapshots for a subject."""
    profile = db.scalars(
        select(UserProfile).where(UserProfile.subject_id == subject_id)
    ).first()
    if not profile or not profile.user_id:
        raise HTTPException(status_code=404, detail=f"Subject {subject_id} not found")

    q = (
        select(FeatureSnapshot)
        .where(FeatureSnapshot.user_id == profile.user_id)
        .order_by(FeatureSnapshot.computed_at.desc())
    )
    if window:
        q = q.where(FeatureSnapshot.window == window)

    q = q.limit(10)
    snaps = db.scalars(q).all()

    return [
        FeatureSnapshotOut(
            user_id=str(s.user_id),
            subject_id=subject_id,
            window=s.window,
            computed_at=s.computed_at,
            features=s.features,
        )
        for s in snaps
    ]


@router.post("/features/recompute", summary="Recompute all features")
def recompute_features(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Force recompute feature snapshots for all subjects."""
    return compute_all_features(db)


# ---------------------------------------------------------------------------
# Subject listing
# ---------------------------------------------------------------------------


@router.get("/subjects", summary="List all imported subjects")
def list_subjects(db: Session = Depends(get_db)) -> list[dict]:
    """Return all known study subjects with their profile data."""
    profiles = db.scalars(
        select(UserProfile).order_by(UserProfile.subject_id)
    ).all()
    return [
        {
            "subject_id": p.subject_id,
            "user_id": str(p.user_id) if p.user_id else None,
            "sex": p.sex,
            "age": p.age,
            "cohort": p.cohort,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in profiles
    ]
