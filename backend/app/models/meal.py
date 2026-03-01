import enum
import uuid

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.compat import JSONB, UUID, StringArray

from app.db.base import Base


class PhotoStatus(str, enum.Enum):
    uploaded = "uploaded"
    processed = "processed"
    failed = "failed"


class MealTsSource(str, enum.Enum):
    user_confirmed = "user_confirmed"
    exif = "exif"
    inferred_from_glucose = "inferred_from_glucose"
    uploaded_at = "uploaded_at"


class MealPhoto(Base):
    __tablename__ = "meal_photos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)
    uploaded_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    image_object_key: Mapped[str] = mapped_column(String, nullable=False)
    exif_ts: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    status: Mapped[PhotoStatus] = mapped_column(Enum(PhotoStatus), default=PhotoStatus.uploaded, nullable=False)
    vision_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    calorie_estimate_kcal: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)


class Meal(Base):
    __tablename__ = "meals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)

    meal_ts: Mapped[DateTime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    meal_ts_source: Mapped[MealTsSource] = mapped_column(
        Enum(MealTsSource),
        default=MealTsSource.uploaded_at,
        nullable=False,
    )

    kcal: Mapped[int] = mapped_column(Integer, nullable=False)
    tags: Mapped[list[str]] = mapped_column(StringArray(), default=list, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    photo_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("meal_photos.id"), nullable=True)


Index("ix_meals_user_ts", Meal.user_id, Meal.meal_ts)
