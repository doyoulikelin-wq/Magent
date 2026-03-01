import uuid

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.compat import UUID

from app.db.base import Base


class UserProfile(Base):
    """Extended profile for study subjects (SCxxx).

    Linked optionally to the auth ``users`` table so batch-imported
    subjects can exist independently of the login system.
    """

    __tablename__ = "user_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    subject_id: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)  # "SC003"

    display_name: Mapped[str | None] = mapped_column(String, nullable=True)
    sex: Mapped[str | None] = mapped_column(String(10), nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    liver_risk_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cohort: Mapped[str] = mapped_column(String(20), default="cgm", nullable=False)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
