"""add user_settings, update agent_actions for payload contract

Revision ID: 0003_intervention_levels
Revises: 0002_agentic
Create Date: 2026-03-01 12:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_intervention_levels"
down_revision = "0002_agentic"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -- user_settings --
    op.create_table(
        "user_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("intervention_level", sa.String(4), nullable=False, server_default="L2"),
        sa.Column("daily_reminder_limit", sa.Integer(), nullable=True),
        sa.Column("allow_auto_escalation", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(op.f("ix_user_settings_user_id"), "user_settings", ["user_id"], unique=True)

    # -- agent_actions: add new columns --
    op.add_column(
        "agent_actions",
        sa.Column("payload_version", sa.String(16), nullable=False, server_default="1.0.0"),
    )
    op.add_column(
        "agent_actions",
        sa.Column(
            "status",
            sa.Enum("valid", "invalid", "degraded", name="actionstatus"),
            nullable=False,
            server_default="valid",
        ),
    )
    op.add_column(
        "agent_actions",
        sa.Column("priority", sa.String(10), nullable=True),
    )
    op.add_column(
        "agent_actions",
        sa.Column("error_code", sa.String(64), nullable=True),
    )
    op.add_column(
        "agent_actions",
        sa.Column("trace_id", sa.String(64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("agent_actions", "trace_id")
    op.drop_column("agent_actions", "error_code")
    op.drop_column("agent_actions", "priority")
    op.drop_column("agent_actions", "status")
    op.drop_column("agent_actions", "payload_version")
    op.execute("DROP TYPE IF EXISTS actionstatus")

    op.drop_index(op.f("ix_user_settings_user_id"), table_name="user_settings")
    op.drop_table("user_settings")
