from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user_id, get_db
from app.models.glucose import GlucoseReading
from app.schemas.glucose import GlucoseImportResponse, GlucoseSummary
from app.services.etl.glucose_etl import _parse_clarity_csv  # noqa: PLC2701
from app.services.glucose_service import get_glucose_points, get_glucose_summary
from app.utils.csv_import import parse_glucose_payload

router = APIRouter()

DATA_DIR = Path(getattr(settings, "DATA_DIR", "/app/data"))


@router.get("/samples")
def list_sample_files() -> list[dict]:
    """List available sample glucose CSV files in the data directory."""
    glucose_dir = DATA_DIR / "glucose"
    if not glucose_dir.is_dir():
        return []
    files = sorted(glucose_dir.glob("*.csv"))
    return [
        {
            "filename": f.name,
            "subject_id": f.stem.replace("Clarity_Export_", ""),
            "size_kb": round(f.stat().st_size / 1024, 1),
        }
        for f in files
    ]


@router.get("/meal-samples")
def list_meal_sample_files() -> list[dict]:
    """List available meal / activity CSV files in the data directory."""
    result = []
    for name in ["activity_food.csv", "index_corrected.csv", "index_corrected_oncurve.csv", "index.csv"]:
        p = DATA_DIR / name
        if p.is_file():
            result.append({
                "filename": name,
                "size_kb": round(p.stat().st_size / 1024, 1),
            })
    return result


@router.post("/import-sample", response_model=GlucoseImportResponse)
def import_sample_glucose(
    filename: str = Query(..., description="Filename from /samples list"),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Import a sample glucose CSV from the data directory (Clarity format)."""
    filepath = (DATA_DIR / "glucose" / filename).resolve()
    # Security: ensure the resolved path is under DATA_DIR/glucose
    glucose_dir = (DATA_DIR / "glucose").resolve()
    if not str(filepath).startswith(str(glucose_dir)) or not filepath.is_file():
        raise HTTPException(status_code=404, detail=f"Sample file not found: {filename}")
    # Use the Clarity parser which handles EGV rows and mmol/L → mg/dL
    rows = _parse_clarity_csv(filepath)
    if not rows:
        return GlucoseImportResponse(inserted=0, skipped=0, errors=[{"row": None, "reason": "No EGV rows found in file"}])
    inserted = 0
    skipped = 0
    errors: list[dict] = []
    for row in rows:
        record = GlucoseReading(
            user_id=user_id,
            ts=row["ts"],
            glucose_mgdl=row["glucose_mgdl"],
            source="sample_import",
            meta={},
        )
        db.add(record)
        inserted += 1
    db.commit()
    return GlucoseImportResponse(inserted=inserted, skipped=skipped, errors=errors)


@router.post("/import", response_model=GlucoseImportResponse)
async def import_glucose(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    payload = await file.read()
    rows, errors = parse_glucose_payload(file.filename or "import.csv", payload)

    inserted = 0
    skipped = len(errors)

    for row in rows:
        glucose = row["glucose_mgdl"]
        if glucose < 20 or glucose > 600:
            skipped += 1
            errors.append({"row": None, "reason": f"out-of-range glucose={glucose}"})
            continue

        record = GlucoseReading(
            user_id=user_id,
            ts=row["ts"],
            glucose_mgdl=glucose,
            source="manual_import",
            meta={},
        )
        db.add(record)
        inserted += 1

    db.commit()

    return GlucoseImportResponse(inserted=inserted, skipped=skipped, errors=errors)


@router.get("/range")
def glucose_range(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Return the min/max timestamp of all glucose data for this user."""
    row = db.execute(
        select(func.min(GlucoseReading.ts), func.max(GlucoseReading.ts), func.count(GlucoseReading.id))
        .where(GlucoseReading.user_id == user_id)
    ).one()
    if row[2] == 0:
        return {"min_ts": None, "max_ts": None, "count": 0}
    return {
        "min_ts": row[0].isoformat() if row[0] else None,
        "max_ts": row[1].isoformat() if row[1] else None,
        "count": row[2],
    }


@router.get("")
def list_glucose(
    from_ts: datetime = Query(alias="from"),
    to_ts: datetime = Query(alias="to"),
    limit: int = Query(default=2000, ge=1, le=10000),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    if to_ts <= from_ts:
        raise HTTPException(status_code=400, detail={"error_code": "BAD_RANGE", "message": "to must be > from"})

    rows = get_glucose_points(db, user_id, from_ts, to_ts)
    # Down-sample if too many points
    if len(rows) > limit:
        step = len(rows) / limit
        rows = [rows[int(i * step)] for i in range(limit)]
    return [
        {
            "id": str(r.id),
            "ts": r.ts,
            "glucose_mgdl": r.glucose_mgdl,
            "source": r.source,
        }
        for r in rows
    ]


@router.get("/summary", response_model=GlucoseSummary)
def summary(
    window: str = Query(default="24h", pattern="^(24h|7d|30d)$"),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        result = get_glucose_summary(db, user_id, window)
        return GlucoseSummary(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"error_code": "BAD_WINDOW", "message": str(exc)}) from exc
