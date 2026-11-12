"""Test Providers built on the standard library, so these tests do not depend on other packages."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any, ClassVar, Self

import pytest

from orchestrator_core import ConfigSection
from orchestrator_sql import (
    Column,
    SqlError,
    SqlIntegrityError,
    SqlProgrammingError,
    SqlProvider,
    SqlSession,
    SqlType,
    Table,
)


class StdlibSqlite(SqlProvider):
    """Minimal SQLite Provider for the Capability tests."""

    dialect: ClassVar[str] = "sqlite"
    paramstyle: ClassVar[str] = "named"

    def __init__(self, database: str = ":memory:") -> None:
        self.database = database

    @classmethod
    def from_config(cls, section: ConfigSection) -> Self:
        section.check_keys(("database",))
        return cls(section.get_str("database", ":memory:"))

    def connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database, autocommit=True)

    def is_driver_error(self, error: BaseException) -> bool:
        return isinstance(error, sqlite3.Error)

    def translate_error(self, error: BaseException) -> SqlError:
        if isinstance(error, sqlite3.IntegrityError):
            return SqlIntegrityError(str(error))
        if isinstance(error, sqlite3.OperationalError):
            return SqlProgrammingError(str(error))
        return SqlError(str(error))

    def column_type(self, sql_type: SqlType) -> str:
        return {SqlType.BOOLEAN: "INTEGER", SqlType.DATE: "TEXT"}.get(sql_type, sql_type.upper())

    def savepoint_statements(self, name: str) -> tuple[str, str, str]:
        return (f"SAVEPOINT {name}", f"RELEASE {name}", f"ROLLBACK TO {name}")


class QmarkSqlite(StdlibSqlite):
    """Same engine, but the driver is told to use ``?`` placeholders."""

    paramstyle: ClassVar[str] = "qmark"


class RecordingCursor:
    """DB-API cursor double that records statements."""

    def __init__(self, log: list[tuple[str, Any]]) -> None:
        self.log = log
        self.description: list[tuple[str, None]] | None = None
        self.rowcount = 1

    def execute(self, operation: str, parameters: Any = None) -> None:
        self.log.append((operation, parameters))
        self.description = [("value", None)]

    def executemany(self, operation: str, seq_of_parameters: Any) -> None:
        self.log.append((operation, list(seq_of_parameters)))

    def fetchall(self) -> list[tuple[int]]:
        return [(1,)]

    def close(self) -> None:
        pass


class RecordingConnection:
    def __init__(self) -> None:
        self.log: list[tuple[str, Any]] = []

    def cursor(self) -> RecordingCursor:
        return RecordingCursor(self.log)

    def close(self) -> None:
        pass


def recording_provider(style: str) -> type[StdlibSqlite]:
    class Recording(StdlibSqlite):
        paramstyle: ClassVar[str] = style

        def connect(self) -> RecordingConnection:  # type: ignore[override]
            return RecordingConnection()

    return Recording


PEOPLE = Table.define(
    "people",
    [
        Column("id", SqlType.INTEGER, primary_key=True),
        Column("name", SqlType.TEXT, nullable=False),
        Column("email", SqlType.TEXT, unique=True),
        Column("team", SqlType.TEXT),
    ],
)


@pytest.fixture
def fakes() -> SimpleNamespace:
    """Test Providers and the table used by the tests."""
    return SimpleNamespace(
        StdlibSqlite=StdlibSqlite,
        QmarkSqlite=QmarkSqlite,
        recording_provider=recording_provider,
        PEOPLE=PEOPLE,
    )


@pytest.fixture(params=[StdlibSqlite, QmarkSqlite], ids=["named", "qmark"])
def session(request: pytest.FixtureRequest) -> Iterator[SqlSession]:
    """Session on an in-memory database with the ``people`` table, for both paramstyles."""
    provider = request.param()
    session = SqlSession(provider, provider.connect())
    session.create_table(PEOPLE)
    yield session
    session.close()
