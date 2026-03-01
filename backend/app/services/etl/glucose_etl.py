"""Batch ETL for Dexcom Clarity glucose CSV files.

Reads all ``data/glucose/Clarity_Export_SCxxx.csv`` files, extracts EGV
rows, converts mmol/L → mg/dL, and bulk-inserts into ``glucose_readings``.
A ``user_profiles`` row is created for each new subject.
"""

from __future__ import annotations

import csv
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.glucose import GlucoseReading
from app.models.user import User
from app.models.user_profile import UserProfile

logger = logging.getLogger(__name__)

MMOL_TO_MGDL = 18.0182
GLUCOSE_CSV_PATTERN = re.compile(r"Clarity_Export_(SC\d+)\.csv")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_subject_id(filename: str) -> str | None:
    m = GLUCOSE_CSV_PATTERN.search(filename)
    return m.group(1) if m else None


def _get_or_create_profile(db: Session, subject_id: str) -> UserProfile:
    """Return an existing profile or create placeholder User + UserProfile."""
    profile = db.scalars(select(UserProfile).where(UserProfile.subject_id == subject_id)).first()
    if profile:
        return profile

    # Create a placeholder auth-user so FK constraints are satisfied
    placeholder = User(
        email=f"{subject_id.lower()}@study.local",
        password_hash="!etl_placeholder",
    )
    db.add(placeholder)
    db.flush()  # get placeholder.id

    profile = UserProfile(
        user_id=placeholder.id,
        subject_id=subject_id,
        cohort="cgm",
    )
    db.add(profile)
    db.flush()
    logger.info("Created placeholder user + profile for %s", subject_id)
    return profile


def _parse_clarity_csv(path: Path) -> list[dict]:
    """Parse a single Dexcom Clarity CSV, returning list of EGV dicts."""
    rows: list[dict] = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        # Skip lines until we find the actual header row (contains 'Timestamp')
        header_line: str | None = None
        for line in fh:
            if "Timestamp" in line and "Event Type" in line:
                header_line = line
                break
        if header_line is None:
            logger.warning("No header row found in %s, skipping", path.name)
            return rows

        # Re-parse from the header onwards
        reader = csv.DictReader([header_line] + fh.readlines())
        for row in reader:
            event_type = (row.get("Event Type") or "").strip()
            if event_type != "EGV":
                continue

            ts_raw = row.get("Timestamp (YYYY-MM-DDThh:mm:ss)") or ""
            glucose_raw = row.get("Glucose Value (mmol/L)") or ""
            if not ts_raw or not glucose_raw:
                continue

            try:
                ts = datetime.fromisoformat(ts_raw).replace(tzinfo=timezone.utc)
                glucose_mmol = float(glucose_raw)
                glucose_mgdl = round(glucose_mmol * MMOL_TO_MGDL)
            except (ValueError, TypeError):
                continue

            if glucose_mgdl < 20 or glucose_mgdl > 600:
                continue

            rows.append({"ts": ts, "glucose_mgdl": glucose_mgdl})

    return rows


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_glucose_etl(
    db: Session,
    data_dir: str | Path,
    *,
    batch_size: int = 2000,
) -> dict:
    """Import all Clarity CSVs from *data_dir*/glucose/ into the database.

    Returns a summary dict with counts.
    """
    data_dir = Path(data_dir)
    glucose_dir = data_dir / "glucose"
    if not glucose_dir.is_dir():
        raise FileNotFoundError(f"Glucose directory not found: {glucose_dir}")

    csv_files = sorted(glucose_dir.glob("Clarity_Export_SC*.csv"))
    logger.info("Found %d glucose CSV files", len(csv_files))

    stats = {"files": 0, "subjects": 0, "rows_inserted": 0, "rows_skipped_dup": 0}

    for csv_path in csv_files:
        subject_id = _extract_subject_id(csv_path.name)
        if not subject_id:
            logger.warning("Cannot extract subject from %s", csv_path.name)
            continue

        profile = _get_or_create_profile(db, subject_id)
        user_id = profile.user_id

        # Check existing min/max ts to avoid full duplicates
        existing = db.execute(
            select(GlucoseReading.ts)
            .where(GlucoseReading.user_id == user_id)
            .order_by(GlucoseReading.ts.desc())
            .limit(1)
        ).scalar()

        rows = _parse_clarity_csv(csv_path)
        if not rows:
            logger.info("No EGV data in %s", csv_path.name)
            continue

        # Deduplicate against existing latest ts
        if existing:
            before = len(rows)
            rows = [r for r in rows if r["ts"] > existing]
            stats["rows_skipped_dup"] += before - len(rows)

        # Bulk insert in batches
        objects: list[GlucoseReading] = []
        for r in rows:
            objects.append(
                GlucoseReading(
                    user_id=user_id,
                    ts=r["ts"],
                    glucose_mgdl=r["glucose_mgdl"],
                    source="clarity_csv_import",
                    meta={"file": csv_path.name},
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

        stats["files"] += 1
        stats["subjects"] += 1
        logger.info(
            "Imported %d readings for %s from %s",
            len(rows),
            subject_id,
            csv_path.name,
        )

    db.commit()
    logger.info("Glucose ETL complete: %s", stats)
    return stats
