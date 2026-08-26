"""Add mobile number + OTP login, relax email/password to optional.

Revision ID: 0004_mobile_otp_login
Revises: 0003_call_recordings
Create Date: 2026-08-17
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_mobile_otp_login"
down_revision: str | None = "0003_call_recordings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("mobile_number", sa.String(length=20), nullable=False))
        batch_op.alter_column("email", existing_type=sa.String(length=320), nullable=True)
        batch_op.alter_column(
            "password_hash", existing_type=sa.String(length=255), nullable=True
        )
        batch_op.create_index(
            batch_op.f("ix_users_mobile_number"), ["mobile_number"], unique=True
        )

    op.create_table(
        "otp_codes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("mobile_number", sa.String(length=20), nullable=False),
        sa.Column("code", sa.String(length=6), nullable=False),
        sa.Column("purpose", sa.String(length=40), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("otp_codes", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_otp_codes_mobile_number"), ["mobile_number"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("otp_codes", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_otp_codes_mobile_number"))
    op.drop_table("otp_codes")

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_users_mobile_number"))
        batch_op.alter_column(
            "password_hash", existing_type=sa.String(length=255), nullable=False
        )
        batch_op.alter_column("email", existing_type=sa.String(length=320), nullable=False)
        batch_op.drop_column("mobile_number")
