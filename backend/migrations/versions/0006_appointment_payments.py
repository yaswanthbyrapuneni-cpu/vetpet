"""Add Razorpay payment fields to appointments.

Revision ID: 0006_appointment_payments
Revises: 0005_consultation_attachments
Create Date: 2026-08-17
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_appointment_payments"
down_revision: str | None = "0005_consultation_attachments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("appointments", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "payment_status",
                sa.Enum("PENDING", "PAID", "FAILED", name="paymentstatus"),
                nullable=False,
                server_default="PENDING",
            )
        )
        batch_op.add_column(
            sa.Column(
                "payment_amount_paise", sa.Integer(), nullable=False, server_default="0"
            )
        )
        batch_op.add_column(sa.Column("razorpay_order_id", sa.String(length=100), nullable=True))
        batch_op.add_column(
            sa.Column("razorpay_payment_id", sa.String(length=100), nullable=True)
        )
        batch_op.create_index(
            batch_op.f("ix_appointments_payment_status"), ["payment_status"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("appointments", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_appointments_payment_status"))
        batch_op.drop_column("razorpay_payment_id")
        batch_op.drop_column("razorpay_order_id")
        batch_op.drop_column("payment_amount_paise")
        batch_op.drop_column("payment_status")
