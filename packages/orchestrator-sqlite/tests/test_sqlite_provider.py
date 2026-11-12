from __future__ import annotations

import sqlite3
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from orchestrator_core import (
    CapabilityUnavailableError,
    ConfigSection,
    ConfigurationError,
    ExecutionContext,
    RetryPolicy,
    RuntimeBuilder,
)
from orchestrator_sql import (
    SqlCapability,
    SqlConnectionError,
    SqlError,
    SqlIntegrityError,
    SqlOperationalError,
    SqlProgrammingError,
    SqlSession,
    SqlType,
)
from orchestrator_sqlite import MEMORY, SqliteProvider


def test_configuration() -> None:
    provider = SqliteProvider.from_config(
        ConfigSection(
            {"database": "x.db", "timeout": "2.5", "read_only": "yes"},
            "capabilities.sql",
        )
    )
    assert provider.database == "x.db"
    assert provider.describe() == "sqlite:x.db"
    assert SqliteProvider.from_config(ConfigSection({})).database == MEMORY
    with pytest.raises(ConfigurationError, match="unknown key"):
        SqliteProvider.from_config(ConfigSection({"path": "x.db"}))
    with pytest.raises(ConfigurationError, match="must be >= 0"):
        SqliteProvider.from_config(ConfigSection({"timeout": -1}))


def test_verify(tmp_path: Path) -> None:
    SqliteProvider().verify()
    SqliteProvider(tmp_path / "new.db").verify()
    with pytest.raises(CapabilityUnavailableError, match="folder of the SQLite database"):
        SqliteProvider(tmp_path / "missing" / "x.db").verify()
    with pytest.raises(CapabilityUnavailableError, match="database not found"):
        SqliteProvider(tmp_path / "absent.db", read_only=True).verify()
    with pytest.raises(CapabilityUnavailableError, match="cannot be read-only"):
        SqliteProvider(read_only=True).verify()


def test_read_only_databases_reject_writes(tmp_path: Path) -> None:
    path = tmp_path / "ro.db"
    writer = SqlSession(SqliteProvider(path), SqliteProvider(path).connect())
    writer.execute("CREATE TABLE t (x INTEGER)")
    writer.insert("t", {"x": 1})
    writer.close()
    reader_provider = SqliteProvider(path, read_only=True)
    reader = SqlSession(reader_provider, reader_provider.connect())
    assert reader.scalar("SELECT x FROM t") == 1
    with pytest.raises(SqlOperationalError, match="readonly"):
        reader.insert("t", {"x": 2})
    reader.close()


def test_connection_failures_are_translated(tmp_path: Path) -> None:
    with pytest.raises(SqlConnectionError, match="cannot open SQLite database"):
        SqliteProvider(tmp_path).connect()  # a folder is not a database


@pytest.mark.parametrize(
    ("error", "expected", "retryable"),
    [
        (
            sqlite3.IntegrityError("UNIQUE constraint failed: t.x"),
            SqlIntegrityError,
            False,
        ),
        (sqlite3.OperationalError("database is locked"), SqlOperationalError, True),
        (sqlite3.OperationalError("no such table: t"), SqlProgrammingError, False),
        (
            sqlite3.OperationalError("unable to open database file"),
            SqlConnectionError,
            False,
        ),
        (sqlite3.OperationalError("disk I/O error"), SqlOperationalError, False),
        (sqlite3.ProgrammingError("closed"), SqlProgrammingError, False),
        (sqlite3.DatabaseError("file is not a database"), SqlError, False),
    ],
)
def test_error_translation(error: sqlite3.Error, expected: type[SqlError], retryable: bool) -> None:
    provider = SqliteProvider()
    assert provider.is_driver_error(error)
    translated = provider.translate_error(error)
    assert type(translated) is expected
    assert translated.retryable is retryable
    assert not provider.is_driver_error(ValueError())


def test_value_adaptation_and_types() -> None:
    provider = SqliteProvider()
    assert provider.adapt(True) == 1
    assert provider.adapt(date(2026, 11, 12)) == "2026-11-12"
    assert provider.adapt(datetime(2026, 11, 12, 1, 2, tzinfo=UTC)) == "2026-11-12T01:02:00+00:00"
    assert provider.adapt(Decimal("1.10")) == "1.10"
    assert provider.adapt("x") == "x"
    assert {provider.column_type(t) for t in SqlType} == {
        "TEXT",
        "INTEGER",
        "REAL",
        "NUMERIC",
        "BLOB",
    }


def test_foreign_keys_are_enforced_by_default(tmp_path: Path) -> None:
    provider = SqliteProvider(tmp_path / "fk.db")
    session = SqlSession(provider, provider.connect())
    session.execute("CREATE TABLE parent (id INTEGER PRIMARY KEY)")
    session.execute("CREATE TABLE child (id INTEGER, parent_id INTEGER REFERENCES parent(id))")
    with pytest.raises(SqlIntegrityError, match="FOREIGN KEY"):
        session.insert("child", {"id": 1, "parent_id": 99})
    session.close()


def test_locked_database_is_retried_through_the_context(tmp_path: Path) -> None:
    """A lock held by another connection is transient: ctx.retry succeeds once it is released."""
    path = tmp_path / "locked.db"
    setup = SqlSession(SqliteProvider(path), SqliteProvider(path).connect())
    setup.execute("CREATE TABLE t (x INTEGER)")
    setup.close()
    blocker = sqlite3.connect(path, autocommit=True)
    blocker.execute("BEGIN EXCLUSIVE")
    attempts: list[int] = []
    runtime = (
        RuntimeBuilder()
        .with_environment({}, prefix=None)
        .with_capability(SqlCapability(SqliteProvider(path, timeout=0)))
        .build()
    )

    def automation(ctx: ExecutionContext) -> int:
        sql = ctx.capability(SqlCapability)

        def write() -> int:
            attempts.append(1)
            if len(attempts) == 2:
                blocker.execute("COMMIT")
            return sql.insert("t", {"x": 1})

        return ctx.retry(write, RetryPolicy.fixed(3, 0.01), name="insert")

    result = runtime.run(automation)
    blocker.close()
    assert result.succeeded, result
    assert len(attempts) == 2  # the first attempt hit the lock
