"""initial schema

Revision ID: 0001_init
Revises:
Create Date: 2026-02-18 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "consents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("allow_ai_chat", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("allow_data_upload", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("version", sa.String(), nullable=False, server_default="v1"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_consents_user_id"), "consents", ["user_id"], unique=False)

    op.create_table(
        "glucose_readings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("glucose_mgdl", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_glucose_readings_ts"), "glucose_readings", ["ts"], unique=False)
    op.create_index(op.f("ix_glucose_readings_user_id"), "glucose_readings", ["user_id"], unique=False)
    op.create_index("ix_glucose_user_ts", "glucose_readings", ["user_id", "ts"], unique=False)

    op.create_table(
        "meal_photos",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("image_object_key", sa.String(), nullable=False),
        sa.Column("exif_ts", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Enum("uploaded", "processed", "failed", name="photostatus"), nullable=False),
        sa.Column("vision_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("calorie_estimate_kcal", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_meal_photos_user_id"), "meal_photos", ["user_id"], unique=False)

    op.create_table(
        "meals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("meal_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "meal_ts_source",
            sa.Enum("user_confirmed", "exif", "inferred_from_glucose", "uploaded_at", name="mealtssource"),
            nullable=False,
        ),
        sa.Column("kcal", sa.Integer(), nullable=False),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("photo_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["photo_id"], ["meal_photos.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_meals_meal_ts"), "meals", ["meal_ts"], unique=False)
    op.create_index(op.f("ix_meals_user_id"), "meals", ["user_id"], unique=False)
    op.create_index("ix_meals_user_ts", "meals", ["user_id", "meal_ts"], unique=False)

    op.create_table(
        "symptoms",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("severity", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_symptoms_ts"), "symptoms", ["ts"], unique=False)
    op.create_index(op.f("ix_symptoms_user_id"), "symptoms", ["user_id"], unique=False)
    op.create_index("ix_symptoms_user_ts", "symptoms", ["user_id", "ts"], unique=False)

    op.create_table(
        "llm_audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("context_hash", sa.String(), nullable=False),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_llm_audit_logs_user_id"), "llm_audit_logs", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_llm_audit_logs_user_id"), table_name="llm_audit_logs")
    op.drop_table("llm_audit_logs")
    op.drop_index("ix_symptoms_user_ts", table_name="symptoms")
    op.drop_index(op.f("ix_symptoms_user_id"), table_name="symptoms")
    op.drop_index(op.f("ix_symptoms_ts"), table_name="symptoms")
    op.drop_table("symptoms")
    op.drop_index("ix_meals_user_ts", table_name="meals")
    op.drop_index(op.f("ix_meals_user_id"), table_name="meals")
    op.drop_index(op.f("ix_meals_meal_ts"), table_name="meals")
    op.drop_table("meals")
    op.drop_index(op.f("ix_meal_photos_user_id"), table_name="meal_photos")
    op.drop_table("meal_photos")
    op.drop_index("ix_glucose_user_ts", table_name="glucose_readings")
    op.drop_index(op.f("ix_glucose_readings_user_id"), table_name="glucose_readings")
    op.drop_index(op.f("ix_glucose_readings_ts"), table_name="glucose_readings")
    op.drop_table("glucose_readings")
    op.drop_index(op.f("ix_consents_user_id"), table_name="consents")
    op.drop_table("consents")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS photostatus")
    op.execute("DROP TYPE IF EXISTS mealtssource")
