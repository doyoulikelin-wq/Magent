import enum
import uuid

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.compat import JSONB, UUID

from app.db.base import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ActionType(str, enum.Enum):
    pre_meal_sim = "pre_meal_sim"
    rescue = "rescue"
    daily_plan = "daily_plan"
    weekly_goal = "weekly_goal"


class ActionStatus(str, enum.Enum):
    valid = "valid"
    invalid = "invalid"
    degraded = "degraded"


class FeedbackChoice(str, enum.Enum):
    executed = "executed"
    not_executed = "not_executed"
    partial = "partial"


# ---------------------------------------------------------------------------
# AgentState – one row per user, updated in-place
# ---------------------------------------------------------------------------


class AgentState(Base):
    __tablename__ = "agent_states"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), unique=True, index=True, nullable=False
    )

    current_goal: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    risk_windows_today: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    active_plan: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    last_replan_ts: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    state_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


# ---------------------------------------------------------------------------
# AgentAction – immutable log of every action the agent takes
# ---------------------------------------------------------------------------


class AgentAction(Base):
    __tablename__ = "agent_actions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False
    )
    action_type: Mapped[ActionType] = mapped_column(Enum(ActionType), nullable=False)
    payload_version: Mapped[str] = mapped_column(String(16), default="1.0.0", nullable=False)
    status: Mapped[ActionStatus] = mapped_column(
        Enum(ActionStatus), default=ActionStatus.valid, nullable=False
    )
    priority: Mapped[str | None] = mapped_column(String(10), nullable=True)  # low / medium / high
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    reason_evidence: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_ts: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


Index("ix_agent_actions_user_ts", AgentAction.user_id, AgentAction.created_ts)


# ---------------------------------------------------------------------------
# OutcomeFeedback – closed-loop evaluation per action
# ---------------------------------------------------------------------------


class OutcomeFeedback(Base):
    __tablename__ = "outcome_feedbacks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_actions.id"), index=True, nullable=False
    )
    user_feedback: Mapped[FeedbackChoice | None] = mapped_column(Enum(FeedbackChoice), nullable=True)
    objective_outcome: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    closed_loop_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_ts: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
