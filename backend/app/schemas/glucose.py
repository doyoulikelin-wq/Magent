from datetime import datetime

from pydantic import BaseModel, Field


class GlucosePoint(BaseModel):
    ts: datetime
    glucose_mgdl: int = Field(ge=20, le=600)


class GlucoseImportResponse(BaseModel):
    inserted: int
    skipped: int
    errors: list[dict]


class GlucoseSummary(BaseModel):
    window: str
    avg: float | None
    min: int | None
    max: int | None
    tir_70_180_pct: float | None
    variability: str
    gaps_hours: float
