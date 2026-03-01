"""add agentic service tables

Revision ID: 0002_agentic
Revises: 0001_init
Create Date: 2026-03-01 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_agentic"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -- user_profiles --
    op.create_table(
        "user_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("subject_id", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=True),
        sa.Column("sex", sa.String(10), nullable=True),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("height_cm", sa.Float(), nullable=True),
        sa.Column("weight_kg", sa.Float(), nullable=True),
        sa.Column("liver_risk_level", sa.String(20), nullable=True),
        sa.Column("cohort", sa.String(20), nullable=False, server_default="cgm"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_profiles_subject_id"), "user_profiles", ["subject_id"], unique=True)
    op.create_index(op.f("ix_user_profiles_user_id"), "user_profiles", ["user_id"], unique=False)

    # -- agent_states --
    op.create_table(
        "agent_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("current_goal", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("risk_windows_today", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("active_plan", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("last_replan_ts", sa.DateTime(timezone=True), nullable=True),
        sa.Column("state_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(op.f("ix_agent_states_user_id"), "agent_states", ["user_id"], unique=True)

    # -- agent_actions --
    op.create_table(
        "agent_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "action_type",
            sa.Enum("pre_meal_sim", "rescue", "daily_plan", "weekly_goal", name="actiontype"),
            nullable=False,
        ),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("reason_evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_ts", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_actions_user_id"), "agent_actions", ["user_id"], unique=False)
    op.create_index("ix_agent_actions_user_ts", "agent_actions", ["user_id", "created_ts"], unique=False)

    # -- outcome_feedbacks --
    op.create_table(
        "outcome_feedbacks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "user_feedback",
            sa.Enum("executed", "not_executed", "partial", name="feedbackchoice"),
            nullable=True,
        ),
        sa.Column("objective_outcome", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("closed_loop_score", sa.Float(), nullable=True),
        sa.Column("created_ts", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["action_id"], ["agent_actions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_outcome_feedbacks_action_id"), "outcome_feedbacks", ["action_id"], unique=False)

    # -- feature_snapshots --
    op.create_table(
        "feature_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("window", sa.String(10), nullable=False),
        sa.Column("features", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_feature_snapshots_user_id"), "feature_snapshots", ["user_id"], unique=False)
    op.create_index("ix_feature_snapshots_user_window", "feature_snapshots", ["user_id", "window"], unique=False)
    op.create_index("ix_feature_snapshots_user_ts", "feature_snapshots", ["user_id", "computed_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_feature_snapshots_user_ts", table_name="feature_snapshots")
    op.drop_index("ix_feature_snapshots_user_window", table_name="feature_snapshots")
    op.drop_index(op.f("ix_feature_snapshots_user_id"), table_name="feature_snapshots")
    op.drop_table("feature_snapshots")

    op.drop_index(op.f("ix_outcome_feedbacks_action_id"), table_name="outcome_feedbacks")
    op.drop_table("outcome_feedbacks")

    op.drop_index("ix_agent_actions_user_ts", table_name="agent_actions")
    op.drop_index(op.f("ix_agent_actions_user_id"), table_name="agent_actions")
    op.drop_table("agent_actions")

    op.drop_index(op.f("ix_agent_states_user_id"), table_name="agent_states")
    op.drop_table("agent_states")

    op.drop_index(op.f("ix_user_profiles_user_id"), table_name="user_profiles")
    op.drop_index(op.f("ix_user_profiles_subject_id"), table_name="user_profiles")
    op.drop_table("user_profiles")

    op.execute("DROP TYPE IF EXISTS actiontype")
    op.execute("DROP TYPE IF EXISTS feedbackchoice")
