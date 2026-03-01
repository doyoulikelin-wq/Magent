"""Batch ETL for meal / food event data.

Supports two sources:

1. ``data/activity_food.csv``  – raw logged meals
2. ``data/index_corrected_oncurve.csv`` – glucose-aligned & quality-filtered meals

For each meal event the service finds (or creates) the corresponding
``UserProfile`` and inserts into the ``meals`` table.
"""

from __future__ import annotations

import csv
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.meal import Meal, MealTsSource
from app.models.user_profile import UserProfile

logger = logging.getLogger(__name__)

SUBJECT_RE = re.compile(r"(SC\d+)")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_subject_id(raw: str) -> str | None:
    """Pull 'SC003' from strings like 'SC003, Sajidah, Female'."""
    m = SUBJECT_RE.search(raw)
    return m.group(1) if m else None


def _resolve_user_id(db: Session, subject_id: str) -> str | None:
    """Return the user_id (UUID) for a given subject_id, or None."""
    profile = db.scalars(
        select(UserProfile).where(UserProfile.subject_id == subject_id)
    ).first()
    return profile.user_id if profile else None


def _parse_food_timestamp(raw: str) -> datetime | None:
    """Parse 'DD-MM-YYYY h:mm AM/PM' → UTC datetime."""
    for fmt in (
        "%d-%m-%Y %I:%M %p",
        "%d-%m-%Y %I:%M:%S %p",
        "%d/%m/%Y %I:%M %p",
    ):
        try:
            return datetime.strptime(raw.strip(), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _parse_index_timestamp(raw: str) -> datetime | None:
    """Parse 'YYYY-MM-DD HH:MM:SS' → UTC datetime."""
    try:
        return datetime.fromisoformat(raw.strip()).replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def _meal_type_tag(activity_id_raw: str) -> str:
    """Extract meal type from '\"Snack, 34688\"' → 'snack'."""
    lower = activity_id_raw.lower().strip().strip('"')
    for tag in ("breakfast", "lunch", "dinner", "snack"):
        if tag in lower:
            return tag
    return "unknown"


# ---------------------------------------------------------------------------
# Public: import activity_food.csv (raw meals)
# ---------------------------------------------------------------------------


def import_activity_food(
    db: Session,
    data_dir: str | Path,
    *,
    batch_size: int = 1000,
) -> dict:
    """Import ``data/activity_food.csv`` into the ``meals`` table.

    Returns summary dict.
    """
    data_dir = Path(data_dir)
    csv_path = data_dir / "activity_food.csv"
    if not csv_path.exists():
        raise FileNotFoundError(str(csv_path))

    stats = {"rows_read": 0, "rows_inserted": 0, "rows_skipped_no_user": 0, "rows_skipped_parse": 0}
    objects: list[Meal] = []

    with open(csv_path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            stats["rows_read"] += 1
            subject_id = _extract_subject_id(row.get("user_id", ""))
            if not subject_id:
                stats["rows_skipped_parse"] += 1
                continue

            user_id = _resolve_user_id(db, subject_id)
            if not user_id:
                stats["rows_skipped_no_user"] += 1
                continue

            ts = _parse_food_timestamp(row.get("created_timestamp", ""))
            if ts is None:
                stats["rows_skipped_parse"] += 1
                continue

            try:
                kcal = int(float(row.get("total_calories", 0)))
            except (ValueError, TypeError):
                kcal = 0

            food_name = (row.get("food_name") or "").strip()
            tag = _meal_type_tag(row.get("activity_id", ""))

            objects.append(
                Meal(
                    user_id=user_id,
                    meal_ts=ts,
                    meal_ts_source=MealTsSource.user_confirmed,
                    kcal=kcal,
                    tags=[tag] if tag != "unknown" else [],
                    notes=food_name or None,
                )
            )

            if len(objects) >= batch_size:
                db.add_all(objects)
                db.flush()
                stats["rows_inserted"] += len(objects)
                objects = []

    if objects:
        db.add_all(objects)
        db.flush()
        stats["rows_inserted"] += len(objects)

    db.commit()
    logger.info("activity_food ETL: %s", stats)
    return stats


# ---------------------------------------------------------------------------
# Public: import index_corrected_oncurve.csv (quality-filtered meals)
# ---------------------------------------------------------------------------


def import_corrected_meals(
    db: Session,
    data_dir: str | Path,
    *,
    batch_size: int = 1000,
) -> dict:
    """Import ``data/index_corrected_oncurve.csv`` (glucose-aligned meals).

    These entries have ``meal_ts_source = inferred_from_glucose``.
    """
    data_dir = Path(data_dir)
    csv_path = data_dir / "index_corrected_oncurve.csv"
    if not csv_path.exists():
        raise FileNotFoundError(str(csv_path))

    stats = {"rows_read": 0, "rows_inserted": 0, "rows_skipped_no_user": 0, "rows_skipped_parse": 0}
    objects: list[Meal] = []

    with open(csv_path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            stats["rows_read"] += 1
            subject_id = (row.get("SCxxx") or "").strip()
            if not SUBJECT_RE.match(subject_id):
                stats["rows_skipped_parse"] += 1
                continue

            user_id = _resolve_user_id(db, subject_id)
            if not user_id:
                stats["rows_skipped_no_user"] += 1
                continue

            ts = _parse_index_timestamp(row.get("timestamp", ""))
            if ts is None:
                stats["rows_skipped_parse"] += 1
                continue

            try:
                kcal = int(float(row.get("calories", 0)))
            except (ValueError, TypeError):
                kcal = 0

            objects.append(
                Meal(
                    user_id=user_id,
                    meal_ts=ts,
                    meal_ts_source=MealTsSource.inferred_from_glucose,
                    kcal=kcal,
                    tags=[],
                    notes="from index_corrected_oncurve",
                )
            )

            if len(objects) >= batch_size:
                db.add_all(objects)
                db.flush()
                stats["rows_inserted"] += len(objects)
                objects = []

    if objects:
        db.add_all(objects)
        db.flush()
        stats["rows_inserted"] += len(objects)

    db.commit()
    logger.info("corrected meals ETL: %s", stats)
    return stats
