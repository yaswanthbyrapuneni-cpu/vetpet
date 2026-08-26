"""Convert pets.species from free text to a fixed species enum.

No production pet data exists yet for this pre-launch feature, so this
migration recreates the column rather than attempting a text-to-enum data
migration. If real rows exist when this runs, back them up first.

Revision ID: 0007_pet_species_enum
Revises: 0006_appointment_payments
Create Date: 2026-08-17
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_pet_species_enum"
down_revision: str | None = "0006_appointment_payments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

species_enum = sa.Enum(
    "DOG", "CAT", "COW", "BUFFALO", "SHEEP", "GOAT", "COUNTRY_HEN", "FARM_HEN", "OTHER",
    name="petspecies",
)


def upgrade() -> None:
    op.execute("DELETE FROM pets")
    with op.batch_alter_table("pets", schema=None) as batch_op:
        batch_op.drop_column("species")
    with op.batch_alter_table("pets", schema=None) as batch_op:
        batch_op.add_column(sa.Column("species", species_enum, nullable=False))
        batch_op.create_index(batch_op.f("ix_pets_species"), ["species"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("pets", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_pets_species"))
        batch_op.drop_column("species")
    with op.batch_alter_table("pets", schema=None) as batch_op:
        batch_op.add_column(sa.Column("species", sa.String(length=80), nullable=False))
