"""Replace scheduled time-slot booking with instant pay-first booking.

Drops the doctor_availability table and the appointments.availability_id /
scheduled_end columns, adds an online/offline flag doctors can toggle
(doctor_profiles.is_online), and moves appointment attachments from disk
storage to database BLOBs. No production data exists yet for this
pre-launch feature, so existing attachment rows are cleared rather than
migrated file-by-file.

Revision ID: 0010_instant_booking
Revises: 0009_chat_and_ratings
Create Date: 2026-08-20
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_instant_booking"
down_revision: str | None = "0009_chat_and_ratings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("doctor_profiles", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("is_online", sa.Boolean(), nullable=False, server_default=sa.false())
        )

    with op.batch_alter_table("appointments", schema=None) as batch_op:
        batch_op.drop_index("ix_appointments_availability_id")
        batch_op.drop_column("availability_id")
        batch_op.drop_column("scheduled_end")

    op.drop_table("doctor_availability")

    op.execute("DELETE FROM appointment_attachments")
    with op.batch_alter_table("appointment_attachments", schema=None) as batch_op:
        batch_op.drop_column("storage_key")
        batch_op.add_column(sa.Column("data", sa.LargeBinary(), nullable=False))


def downgrade() -> None:
    with op.batch_alter_table("appointment_attachments", schema=None) as batch_op:
        batch_op.drop_column("data")
        batch_op.add_column(sa.Column("storage_key", sa.String(length=500), nullable=False))
    with op.batch_alter_table("appointment_attachments", schema=None) as batch_op:
        batch_op.create_unique_constraint("uq_appointment_attachments_storage_key", ["storage_key"])

    op.create_table(
        "doctor_availability",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("doctor_id", sa.String(length=36), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_booked", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctor_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("doctor_availability", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_doctor_availability_doctor_id"), ["doctor_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_doctor_availability_starts_at"), ["starts_at"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_doctor_availability_ends_at"), ["ends_at"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_doctor_availability_is_booked"), ["is_booked"], unique=False
        )

    with op.batch_alter_table("appointments", schema=None) as batch_op:
        batch_op.add_column(sa.Column("availability_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("scheduled_end", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index(
            "ix_appointments_availability_id", ["availability_id"], unique=False
        )
        batch_op.create_foreign_key(
            "fk_appointments_availability_id_doctor_availability",
            "doctor_availability",
            ["availability_id"],
            ["id"],
        )

    with op.batch_alter_table("doctor_profiles", schema=None) as batch_op:
        batch_op.drop_column("is_online")
