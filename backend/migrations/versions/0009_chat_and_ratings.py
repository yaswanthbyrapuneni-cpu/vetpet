"""Add appointment chat messages and post-consultation ratings.

Revision ID: 0009_chat_and_ratings
Revises: 0008_appointment_attachments
Create Date: 2026-08-18
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_chat_and_ratings"
down_revision: str | None = "0008_appointment_attachments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "appointment_messages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("appointment_id", sa.String(length=36), nullable=False),
        sa.Column("sender_user_id", sa.String(length=36), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["appointment_id"], ["appointments.id"]),
        sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("appointment_messages", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_appointment_messages_appointment_id"),
            ["appointment_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_appointment_messages_sender_user_id"),
            ["sender_user_id"],
            unique=False,
        )

    op.create_table(
        "appointment_ratings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("appointment_id", sa.String(length=36), nullable=False),
        sa.Column("rated_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("stars", sa.Integer(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["appointment_id"], ["appointments.id"]),
        sa.ForeignKeyConstraint(["rated_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("appointment_id"),
    )


def downgrade() -> None:
    op.drop_table("appointment_ratings")
    with op.batch_alter_table("appointment_messages", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_appointment_messages_sender_user_id"))
        batch_op.drop_index(batch_op.f("ix_appointment_messages_appointment_id"))
    op.drop_table("appointment_messages")
