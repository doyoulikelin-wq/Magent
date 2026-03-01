from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PresignRequest(BaseModel):
    filename: str
    content_type: str = "image/jpeg"


class PresignResponse(BaseModel):
    upload_url: str
    object_key: str
    expires_in: int


class PhotoCompleteRequest(BaseModel):
    object_key: str
    exif_ts: datetime | None = None


class MealVisionItem(BaseModel):
    name: str
    portion_text: str
    kcal: int = Field(ge=0, le=5000)


class MealVisionResult(BaseModel):
    items: list[MealVisionItem]
    total_kcal: int = Field(ge=0, le=20000)
    confidence: float = Field(ge=0, le=1)
    notes: str = ""


class MealPhotoOut(BaseModel):
    id: str
    uploaded_at: datetime
    status: str
    calorie_estimate_kcal: int | None
    confidence: float | None
    vision_json: dict
    suggested_meal_ts: datetime | None = None
    suggested_confidence: float | None = None


class MealCreate(BaseModel):
    meal_ts: datetime
    meal_ts_source: Literal["user_confirmed", "exif", "inferred_from_glucose", "uploaded_at"]
    kcal: int = Field(ge=0, le=20000)
    tags: list[str] = []
    photo_id: str | None = None
    notes: str | None = None


class MealUpdate(BaseModel):
    meal_ts: datetime | None = None
    meal_ts_source: Literal["user_confirmed", "exif", "inferred_from_glucose", "uploaded_at"] | None = None
    kcal: int | None = Field(default=None, ge=0, le=20000)
    tags: list[str] | None = None
    notes: str | None = None


class MealOut(BaseModel):
    id: str
    meal_ts: datetime
    meal_ts_source: str
    kcal: int
    tags: list[str]
    notes: str | None
    photo_id: str | None
