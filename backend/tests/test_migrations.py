from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.core.config import get_settings


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
