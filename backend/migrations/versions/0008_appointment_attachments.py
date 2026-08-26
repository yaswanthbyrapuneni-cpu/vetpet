"""Re-key attachments from consultations to appointments so photo/video/voice
sharing works from booking time onward, not only once a consultation exists.

Revision ID: 0008_appointment_attachments
Revises: 0007_pet_species_enum
Create Date: 2026-08-17
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_appointment_attachments"
down_revision: str | None = "0007_pet_species_enum"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _attachment_kind_column() -> sa.Column:
    # 0005 already created the "attachmentkind" Postgres enum type and it's
    # never dropped in between — both directions here just reuse it, they
    # don't own its lifecycle. The generic sa.Enum(...) quietly re-attempts
    # CREATE TYPE on every table that embeds it (create_type=False doesn't
    # suppress this — confirmed against a real Postgres instance), so the
    # dialect-specific class is used here to reference the existing type by
    # name only. SQLite has no real type to reuse, so it keeps declaring the
    # column (and its CHECK constraint) fresh, same as before.
    if op.get_bind().dialect.name == "postgresql":
        kind_type: sa.types.TypeEngine = postgresql.ENUM(name="attachmentkind", create_type=False)
    else:
        kind_type = sa.Enum("PHOTO", "VIDEO", "VOICE", name="attachmentkind")
    return sa.Column("kind", kind_type, nullable=False)


def upgrade() -> None:
    op.drop_table("consultation_attachments")
    op.create_table(
        "appointment_attachments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("appointment_id", sa.String(length=36), nullable=False),
        sa.Column("uploaded_by_user_id", sa.String(length=36), nullable=False),
        _attachment_kind_column(),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["appointment_id"], ["appointments.id"]),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
    )
    with op.batch_alter_table("appointment_attachments", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_appointment_attachments_appointment_id"),
            ["appointment_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_appointment_attachments_uploaded_by_user_id"),
            ["uploaded_by_user_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_appointment_attachments_kind"), ["kind"], unique=False
        )


def downgrade() -> None:
    op.drop_table("appointment_attachments")
    op.create_table(
        "consultation_attachments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("consultation_id", sa.String(length=36), nullable=False),
        sa.Column("uploaded_by_user_id", sa.String(length=36), nullable=False),
        _attachment_kind_column(),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["consultation_id"], ["consultations.id"]),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
    )
    with op.batch_alter_table("consultation_attachments", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_consultation_attachments_consultation_id"),
            ["consultation_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_consultation_attachments_uploaded_by_user_id"),
            ["uploaded_by_user_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_consultation_attachments_kind"), ["kind"], unique=False
        )
