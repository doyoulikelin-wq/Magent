import uuid

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.compat import JSONB, UUID

from app.db.base import Base


class FeatureSnapshot(Base):
    """Stores computed feature vectors per user per time window.

    ``features`` is a JSONB dict containing all computed metrics,
    e.g. {"tir_70_180": 0.82, "cv_24h": 0.19, "rolling_auc_7d": 148.5, ...}
    """

    __tablename__ = "feature_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False
    )
    computed_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    window: Mapped[str] = mapped_column(String(10), nullable=False)  # "24h", "7d", "28d"
    features: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


Index("ix_feature_snapshots_user_window", FeatureSnapshot.user_id, FeatureSnapshot.window)
Index("ix_feature_snapshots_user_ts", FeatureSnapshot.user_id, FeatureSnapshot.computed_at)
