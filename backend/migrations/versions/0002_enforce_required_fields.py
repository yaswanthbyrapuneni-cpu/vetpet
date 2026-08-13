"""Enforce required appointment and prescription fields.

Revision ID: 0002_required_fields
Revises: 000d3091a68f
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_required_fields"
down_revision: str | None = "000d3091a68f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    missing_slots = connection.scalar(
        sa.text("SELECT COUNT(*) FROM appointments WHERE availability_id IS NULL")
    )
    if missing_slots:
        raise RuntimeError(
            "Cannot migrate appointments with no availability slot; repair those rows first"
        )

    if connection.dialect.name == "postgresql":
        connection.execute(
            sa.text(
                "UPDATE prescriptions SET recommended_tests = '[]'::json "
                "WHERE recommended_tests IS NULL"
            )
        )
    else:
        connection.execute(
            sa.text(
                "UPDATE prescriptions SET recommended_tests = '[]' "
                "WHERE recommended_tests IS NULL"
            )
        )

    with op.batch_alter_table("appointments") as batch_op:
        batch_op.alter_column(
            "availability_id",
            existing_type=sa.String(length=36),
            nullable=False,
        )
    with op.batch_alter_table("prescriptions") as batch_op:
        batch_op.alter_column(
            "recommended_tests",
            existing_type=sa.JSON(),
            nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("prescriptions") as batch_op:
        batch_op.alter_column(
            "recommended_tests",
            existing_type=sa.JSON(),
            nullable=True,
        )
    with op.batch_alter_table("appointments") as batch_op:
        batch_op.alter_column(
            "availability_id",
            existing_type=sa.String(length=36),
            nullable=True,
        )
