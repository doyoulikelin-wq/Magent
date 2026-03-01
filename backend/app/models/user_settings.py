import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.compat import UUID

from app.db.base import Base


class UserSettings(Base):
    """User-facing preferences for the Agentic service.

    One row per user.  Created lazily on first access.
    """

    __tablename__ = "user_settings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), unique=True, index=True, nullable=False
    )

    # Intervention level: L1 (温和) / L2 (标准) / L3 (积极)
    intervention_level: Mapped[str] = mapped_column(String(4), default="L2", nullable=False)

    # Daily reminder cap override (must be <= level max)
    daily_reminder_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Allow consecutive-anomaly auto-escalation suggestion
    allow_auto_escalation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
