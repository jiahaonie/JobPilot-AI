"""Unit tests for database engine configuration."""

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.config import Settings
from app.core.database import Database


def test_sqlite_connections_enforce_foreign_keys() -> None:
    database = Database(
        Settings(
            environment="test",
            database_url="sqlite://",
            auto_create_tables=False,
        )
    )
    try:
        with database.engine.begin() as connection:
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
            connection.exec_driver_sql("CREATE TABLE parent (id INTEGER PRIMARY KEY)")
            connection.exec_driver_sql(
                "CREATE TABLE child ("
                "id INTEGER PRIMARY KEY, "
                "parent_id INTEGER NOT NULL REFERENCES parent(id)"
                ")"
            )

        with pytest.raises(IntegrityError):
            with database.engine.begin() as connection:
                connection.exec_driver_sql("INSERT INTO child (id, parent_id) VALUES (1, 999)")
    finally:
        database.dispose()
