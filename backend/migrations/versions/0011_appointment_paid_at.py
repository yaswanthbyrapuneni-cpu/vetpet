"""Record exactly when an appointment's payment settled, for a payment-details/receipt view.

Backfills paid_at from updated_at for appointments already marked paid, as a best-effort
approximation for existing data — new payments going forward get the real timestamp.

Revision ID: 0011_appointment_paid_at
Revises: 0010_instant_booking
Create Date: 2026-08-25
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_appointment_paid_at"
down_revision: str | None = "0010_instant_booking"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("appointments", schema=None) as batch_op:
        batch_op.add_column(sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True))
    # SQLAlchemy's Enum column stores the member's *name* ("PAID"), not its value ("paid").
    op.execute("UPDATE appointments SET paid_at = updated_at WHERE payment_status = 'PAID'")


def downgrade() -> None:
    with op.batch_alter_table("appointments", schema=None) as batch_op:
        batch_op.drop_column("paid_at")
