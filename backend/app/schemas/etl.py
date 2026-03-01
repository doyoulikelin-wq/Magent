from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ETLRunResponse(BaseModel):
    status: str = "ok"
    glucose: dict[str, Any] | None = None
    meals_raw: dict[str, Any] | None = None
    meals_corrected: dict[str, Any] | None = None
    features: dict[str, Any] | None = None
    errors: list[str] | None = None


class FeatureSnapshotOut(BaseModel):
    user_id: str
    subject_id: str
    window: str
    computed_at: datetime
    features: dict[str, Any]

    model_config = {"from_attributes": True}
