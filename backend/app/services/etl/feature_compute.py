"""Feature Store computation layer.

Computes short-term (24h / 7d) and long-term (28d+) metabolic features
for each user and persists them as ``FeatureSnapshot`` rows.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta, timezone

import numpy as np
from sqlalchemy import select, func as sa_func
from sqlalchemy.orm import Session

from app.models.feature import FeatureSnapshot
from app.models.glucose import GlucoseReading
from app.models.meal import Meal
from app.models.user_profile import UserProfile

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Low-level feature calculators
# ---------------------------------------------------------------------------


def _tir(values: list[float], lo: float = 70, hi: float = 180) -> float:
    """Time-in-range as fraction [0, 1]."""
    if not values:
        return 0.0
    return sum(1 for v in values if lo <= v <= hi) / len(values)


def _cv(values: list[float]) -> float:
    """Coefficient of variation."""
    if len(values) < 2:
        return 0.0
    arr = np.array(values, dtype=float)
    mean = arr.mean()
    if mean == 0:
        return 0.0
    return float(arr.std(ddof=1) / mean)


def _auc_above_baseline(
    timestamps: list[datetime],
    glucose: list[float],
    baseline: float,
) -> float:
    """Trapezoidal AUC above baseline (units: mg/dL · min)."""
    if len(timestamps) < 2:
        return 0.0
    total = 0.0
    for i in range(1, len(timestamps)):
        dt_min = (timestamps[i] - timestamps[i - 1]).total_seconds() / 60.0
        g0 = max(glucose[i - 1] - baseline, 0)
        g1 = max(glucose[i] - baseline, 0)
        total += 0.5 * (g0 + g1) * dt_min
    return total


def _night_variability(
    timestamps: list[datetime],
    glucose: list[float],
    night_start: int = 0,
    night_end: int = 6,
) -> float:
    """Std-dev of glucose during night hours."""
    night_vals = [g for ts, g in zip(timestamps, glucose) if night_start <= ts.hour < night_end]
    if len(night_vals) < 2:
        return 0.0
    return float(np.std(night_vals, ddof=1))


# ---------------------------------------------------------------------------
# Per-user feature computation
# ---------------------------------------------------------------------------


def _compute_glucose_features(
    db: Session,
    user_id,
    window_hours: int,
    ref_time: datetime,
) -> dict:
    """Compute glucose-derived features for user in the given window."""
    start = ref_time - timedelta(hours=window_hours)
    rows = db.execute(
        select(GlucoseReading.ts, GlucoseReading.glucose_mgdl)
        .where(GlucoseReading.user_id == user_id)
        .where(GlucoseReading.ts >= start)
        .where(GlucoseReading.ts <= ref_time)
        .order_by(GlucoseReading.ts)
    ).all()

    if not rows:
        return {}

    timestamps = [r.ts for r in rows]
    values = [float(r.glucose_mgdl) for r in rows]

    features: dict = {
        "n_readings": len(values),
        "glucose_mean": round(float(np.mean(values)), 1),
        "glucose_min": float(min(values)),
        "glucose_max": float(max(values)),
        "tir_70_180": round(_tir(values), 4),
        "cv": round(_cv(values), 4),
        "night_variability": round(_night_variability(timestamps, values), 2),
    }

    # Compute rolling AUC above a 'normal' baseline of 100 mg/dL
    features["auc_above_100"] = round(_auc_above_baseline(timestamps, values, 100.0), 1)

    # Gap detection: max gap between consecutive readings (minutes)
    max_gap = 0.0
    for i in range(1, len(timestamps)):
        gap = (timestamps[i] - timestamps[i - 1]).total_seconds() / 60.0
        max_gap = max(max_gap, gap)
    features["max_gap_min"] = round(max_gap, 1)

    return features


def _compute_meal_features(
    db: Session,
    user_id,
    window_hours: int,
    ref_time: datetime,
) -> dict:
    """Compute meal-derived features for user in the given window."""
    start = ref_time - timedelta(hours=window_hours)
    rows = db.execute(
        select(Meal.meal_ts, Meal.kcal)
        .where(Meal.user_id == user_id)
        .where(Meal.meal_ts >= start)
        .where(Meal.meal_ts <= ref_time)
        .order_by(Meal.meal_ts)
    ).all()

    if not rows:
        return {"meal_count": 0}

    kcals = [float(r.kcal) for r in rows]
    return {
        "meal_count": len(kcals),
        "total_kcal": round(sum(kcals)),
        "avg_kcal": round(float(np.mean(kcals)), 1),
        "max_kcal": round(max(kcals)),
    }


def _compute_meal_glucose_response(
    db: Session,
    user_id,
    ref_time: datetime,
    window_days: int = 28,
) -> dict:
    """Estimate per-user calorie→glucose sensitivity slope (long-term)."""
    start = ref_time - timedelta(days=window_days)

    meals = db.execute(
        select(Meal.meal_ts, Meal.kcal)
        .where(Meal.user_id == user_id)
        .where(Meal.meal_ts >= start)
        .where(Meal.meal_ts <= ref_time)
        .where(Meal.kcal > 0)
        .order_by(Meal.meal_ts)
    ).all()

    if len(meals) < 3:
        return {}

    slopes: list[float] = []
    for m in meals:
        # Get peak glucose in 10-120 min after meal
        post_start = m.meal_ts + timedelta(minutes=10)
        post_end = m.meal_ts + timedelta(minutes=120)
        glu_rows = db.execute(
            select(GlucoseReading.glucose_mgdl)
            .where(GlucoseReading.user_id == user_id)
            .where(GlucoseReading.ts >= post_start)
            .where(GlucoseReading.ts <= post_end)
        ).scalars().all()

        if not glu_rows:
            continue

        # Baseline: 30 min before meal
        baseline_start = m.meal_ts - timedelta(minutes=30)
        baseline_rows = db.execute(
            select(GlucoseReading.glucose_mgdl)
            .where(GlucoseReading.user_id == user_id)
            .where(GlucoseReading.ts >= baseline_start)
            .where(GlucoseReading.ts <= m.meal_ts)
        ).scalars().all()

        if not baseline_rows:
            continue

        baseline = float(np.mean(baseline_rows))
        peak = float(max(glu_rows))
        delta = peak - baseline
        if m.kcal > 0:
            slopes.append(delta / m.kcal)

    if not slopes:
        return {}

    return {
        "kcal_response_slope": round(float(np.mean(slopes)), 4),
        "kcal_response_slope_std": round(float(np.std(slopes, ddof=1)) if len(slopes) > 1 else 0.0, 4),
        "n_meals_for_slope": len(slopes),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


WINDOW_MAP = {
    "24h": 24,
    "7d": 24 * 7,
    "28d": 24 * 28,
}


def compute_features_for_user(
    db: Session,
    user_id,
    ref_time: datetime | None = None,
    windows: list[str] | None = None,
) -> list[FeatureSnapshot]:
    """Compute and persist feature snapshots for one user.

    Returns the list of created FeatureSnapshot objects.
    """
    if ref_time is None:
        ref_time = datetime.now(timezone.utc)
    if windows is None:
        windows = list(WINDOW_MAP.keys())

    snapshots: list[FeatureSnapshot] = []

    for w in windows:
        hours = WINDOW_MAP.get(w)
        if hours is None:
            logger.warning("Unknown window %s, skipping", w)
            continue

        features: dict = {}
        features.update(_compute_glucose_features(db, user_id, hours, ref_time))
        features.update(_compute_meal_features(db, user_id, hours, ref_time))

        # Long-term features only for 28d window
        if w == "28d":
            features.update(_compute_meal_glucose_response(db, user_id, ref_time, window_days=28))

        snap = FeatureSnapshot(
            user_id=user_id,
            computed_at=ref_time,
            window=w,
            features=features,
        )
        db.add(snap)
        snapshots.append(snap)

    db.flush()
    return snapshots


def compute_all_features(
    db: Session,
    ref_time: datetime | None = None,
) -> dict:
    """Compute feature snapshots for ALL users with data.

    Returns a summary dict.
    """
    if ref_time is None:
        ref_time = datetime.now(timezone.utc)

    profiles = db.scalars(select(UserProfile).where(UserProfile.cohort == "cgm")).all()
    stats = {"users_processed": 0, "snapshots_created": 0}

    for profile in profiles:
        if not profile.user_id:
            continue
        snaps = compute_features_for_user(db, profile.user_id, ref_time)
        stats["snapshots_created"] += len(snaps)
        stats["users_processed"] += 1

    db.commit()
    logger.info("Feature computation complete: %s", stats)
    return stats
