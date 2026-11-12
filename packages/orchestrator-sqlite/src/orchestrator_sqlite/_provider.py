"""SQLite Provider, based on the standard library ``sqlite3`` module."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import ClassVar, Final, Self
from urllib.parse import quote

from orchestrator_core import CapabilityUnavailableError, ConfigSection
from orchestrator_sql import (
    SqlConnectionError,
    SqlError,
    SqlIntegrityError,
    SqlOperationalError,
    SqlProgrammingError,
    SqlProvider,
    SqlType,
)

MEMORY: Final = ":memory:"
_TYPES: Final = {
    SqlType.TEXT: "TEXT",
    SqlType.INTEGER: "INTEGER",
    SqlType.BIGINT: "INTEGER",
    SqlType.REAL: "REAL",
    SqlType.NUMERIC: "NUMERIC",
    SqlType.BOOLEAN: "INTEGER",
    SqlType.DATE: "TEXT",
    SqlType.TIMESTAMP: "TEXT",
    SqlType.BLOB: "BLOB",
}
_TRANSIENT: Final = (
    "database is locked",
    "database table is locked",
    "database is busy",
)


class SqliteProvider(SqlProvider):
    """Provider for SQLite databases (files or ``:memory:``).

    Configuration keys (``[capabilities.<name>]``):

    * ``database``: file path or ``:memory:`` (default ``:memory:``); the
      parent folder of a file must exist;
    * ``timeout``: seconds to wait for a lock (default 5);
    * ``read_only``: open the file read-only (default false);
    * ``foreign_keys``: enforce foreign keys (default true).

    Dates and timestamps are stored as ISO 8601 text, booleans as 0/1 and
    decimals as text with the NUMERIC affinity. An in-memory database lives
    only as long as one execution's connection.
    """

    dialect: ClassVar[str] = "sqlite"
    paramstyle: ClassVar[str] = "named"

    def __init__(
        self,
        database: str | Path = MEMORY,
        *,
        timeout: float = 5.0,
        read_only: bool = False,
        foreign_keys: bool = True,
    ) -> None:
        """Create the Provider (no connection is opened here)."""
        self._database = str(database)
        self._timeout = timeout
        self._read_only = read_only
        self._foreign_keys = foreign_keys

    @classmethod
    def from_config(cls, section: ConfigSection) -> Self:
        """Create the Provider from its configuration table."""
        section.check_keys(("database", "timeout", "read_only", "foreign_keys"))
        return cls(
            section.get_str("database", MEMORY),
            timeout=section.get_float("timeout", 5.0, minimum=0.0),
            read_only=section.get_bool("read_only", False),
            foreign_keys=section.get_bool("foreign_keys", True),
        )

    @property
    def database(self) -> str:
        """Database path, or ``:memory:``."""
        return self._database

    def verify(self) -> None:
        """Check that the database location is usable."""
        if self._database == MEMORY:
            if self._read_only:
                msg = "an in-memory SQLite database cannot be read-only"
                raise CapabilityUnavailableError(msg)
            return
        path = Path(self._database)
        if self._read_only and not path.is_file():
            msg = f"SQLite database not found: {path}"
            raise CapabilityUnavailableError(msg)
        if not path.parent.is_dir():
            msg = f"folder of the SQLite database does not exist: {path.parent}"
            raise CapabilityUnavailableError(msg)

    def connect(self) -> sqlite3.Connection:
        """Open a connection in autocommit mode."""
        try:
            if self._read_only:
                uri = f"file:{quote(Path(self._database).resolve().as_posix())}?mode=ro"
                connection = sqlite3.connect(uri, timeout=self._timeout, autocommit=True, uri=True)
            else:
                connection = sqlite3.connect(self._database, timeout=self._timeout, autocommit=True)
            if self._foreign_keys:
                connection.execute("PRAGMA foreign_keys = ON")
        except sqlite3.Error as exc:
            msg = f"cannot open SQLite database {self.describe()}: {exc}"
            raise SqlConnectionError(msg, retryable=False) from exc
        return connection

    def is_driver_error(self, error: BaseException) -> bool:
        """Errors of the ``sqlite3`` module are translated."""
        return isinstance(error, sqlite3.Error)

    def translate_error(self, error: BaseException) -> SqlError:  # noqa: PLR0911 - flat mapping
        """Map ``sqlite3`` exceptions to the Capability errors."""
        message = str(error)
        if isinstance(error, sqlite3.IntegrityError):
            return SqlIntegrityError(message)
        if isinstance(error, sqlite3.OperationalError):
            lowered = message.lower()
            if any(marker in lowered for marker in _TRANSIENT):
                return SqlOperationalError(message, retryable=True)
            if (
                "no such table" in lowered
                or "no such column" in lowered
                or "syntax error" in lowered
            ):
                return SqlProgrammingError(message)
            if "unable to open database" in lowered:
                return SqlConnectionError(message, retryable=False)
            return SqlOperationalError(message)
        if isinstance(error, sqlite3.ProgrammingError | sqlite3.InterfaceError):
            return SqlProgrammingError(message)
        return SqlError(message)

    def column_type(self, sql_type: SqlType) -> str:
        """Map portable types to SQLite type affinities."""
        return _TYPES[sql_type]

    def adapt(self, value: object) -> object:
        """Convert values that ``sqlite3`` does not bind natively."""
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, datetime | date):
            return value.isoformat()
        if isinstance(value, Decimal):
            return str(value)
        return value

    def savepoint_statements(self, name: str) -> tuple[str, str, str]:
        """SQLite savepoint statements."""
        return (f"SAVEPOINT {name}", f"RELEASE {name}", f"ROLLBACK TO {name}")

    def describe(self) -> str:
        """Return ``sqlite:<path>`` (no credentials exist in SQLite)."""
        return f"sqlite:{self._database}"
