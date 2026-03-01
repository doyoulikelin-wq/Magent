import uuid

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.compat import JSONB, UUID

from app.db.base import Base


class GlucoseReading(Base):
    __tablename__ = "glucose_readings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)
    ts: Mapped[DateTime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    glucose_mgdl: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String, default="manual_import", nullable=False)
    meta: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


Index("ix_glucose_user_ts", GlucoseReading.user_id, GlucoseReading.ts)
