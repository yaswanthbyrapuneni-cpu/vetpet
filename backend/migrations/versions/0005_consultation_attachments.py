"""Add consultation attachments (photo/video/voice) for owner-doctor sharing.

Revision ID: 0005_consultation_attachments
Revises: 0004_mobile_otp_login
Create Date: 2026-08-17
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_consultation_attachments"
down_revision: str | None = "0004_mobile_otp_login"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "consultation_attachments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("consultation_id", sa.String(length=36), nullable=False),
        sa.Column("uploaded_by_user_id", sa.String(length=36), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("PHOTO", "VIDEO", "VOICE", name="attachmentkind"),
            nullable=False,
        ),
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


def downgrade() -> None:
    op.drop_table("consultation_attachments")
    # This is the type's original creator (0008 only ever reuses it, never
    # owns its lifecycle) and by this point nothing references it anymore.
    sa.Enum(name="attachmentkind").drop(op.get_bind(), checkfirst=True)
