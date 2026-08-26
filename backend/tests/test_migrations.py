import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.domain import (
    Appointment,
    DoctorProfile,
    PaymentStatus,
    Pet,
    PetSpecies,
    User,
    UserRole,
    utc_now,
)


def test_migrations_upgrade_downgrade_and_match_metadata(
    tmp_path: Path, monkeypatch
) -> None:
    database_path = tmp_path / "migration-test.db"
    monkeypatch.setenv("VETPET_DATABASE_URL", f"sqlite:///{database_path.as_posix()}")
    get_settings.cache_clear()
    config = Config("alembic.ini")

    command.upgrade(config, "head")
    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    assert "notifications" in inspect(engine).get_table_names()
    assert "alembic_version" in inspect(engine).get_table_names()
    command.check(config)

    command.downgrade(config, "base")
    assert "users" not in inspect(engine).get_table_names()
    command.upgrade(config, "head")
    assert "users" in inspect(engine).get_table_names()
    engine.dispose()
    get_settings.cache_clear()


@pytest.mark.skipif(
    not os.environ.get("VETPET_TEST_POSTGRES_URL"),
    reason=(
        "Set VETPET_TEST_POSTGRES_URL to a scratch Postgres database to run this. "
        "SQLite has no real enum types, so the equivalent SQLite-only test above "
        "cannot catch Postgres-specific 'CREATE TYPE ... already exists' bugs — "
        "exactly the class of bug this test exists to pin down after one shipped "
        "undetected until a real deploy hit it. Example scratch DB:\n"
        "  docker run --rm -d -p 15432:5432 -e POSTGRES_PASSWORD=vetpet "
        "-e POSTGRES_USER=vetpet -e POSTGRES_DB=vetpet postgres:17-alpine\n"
        "  VETPET_TEST_POSTGRES_URL=postgresql+psycopg://vetpet:vetpet@localhost:15432/vetpet"
    ),
)
def test_migrations_upgrade_downgrade_cycle_on_postgres(monkeypatch) -> None:
    url = os.environ["VETPET_TEST_POSTGRES_URL"]
    monkeypatch.setenv("VETPET_DATABASE_URL", url)
    get_settings.cache_clear()
    config = Config("alembic.ini")
    engine = create_engine(url)
    try:
        # Twice, not once: several migrations only failed the *second* time
        # an enum type was reused (an already-existing type behaves
        # differently than a freshly-created one) — a single upgrade/downgrade
        # pass would have missed that.
        for _ in range(2):
            command.upgrade(config, "head")
            assert "notifications" in inspect(engine).get_table_names()
            command.downgrade(config, "base")
            assert "users" not in inspect(engine).get_table_names()
        command.upgrade(config, "head")
        assert "users" in inspect(engine).get_table_names()
    finally:
        with engine.begin() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
        engine.dispose()
        get_settings.cache_clear()


def test_enum_columns_store_member_name_not_value(db_session: Session) -> None:
    """A raw-SQL migration filtering `WHERE payment_status = 'paid'` (the enum's *value*)
    silently matches zero rows, because SQLAlchemy's Enum column type persists the
    member's *name* ("PAID"). This bit the 0011 migration's backfill until caught by
    hand against real data — pinned here so a future migration doesn't repeat it."""
    owner = User(mobile_number="+910000090001", full_name="Enum Test Owner", role=UserRole.OWNER)
    doctor_user = User(
        mobile_number="+910000090002", full_name="Enum Test Doctor", role=UserRole.DOCTOR
    )
    doctor = DoctorProfile(user=doctor_user, license_number="ENUM-TEST-1", qualification="BVSc")
    pet = Pet(owner=owner, name="Enum Test Pet", species=PetSpecies.DOG)
    db_session.add_all([owner, doctor_user, doctor, pet])
    db_session.flush()
    appointment = Appointment(
        pet_id=pet.id,
        doctor_id=doctor.id,
        scheduled_start=utc_now(),
        reason="test",
        payment_status=PaymentStatus.PAID,
    )
    db_session.add(appointment)
    db_session.commit()

    raw_value = db_session.execute(
        text("SELECT payment_status FROM appointments WHERE id = :id"), {"id": appointment.id}
    ).scalar_one()
    assert raw_value == "PAID"
