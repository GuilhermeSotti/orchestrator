"""Port that SQL Providers implement (one per database engine)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any, ClassVar, Protocol, Self

from orchestrator_core import ConfigSection
from orchestrator_sql._errors import SqlError
from orchestrator_sql._schema import SqlType


class DbapiCursor(Protocol):
    """Subset of a DB-API 2.0 (PEP 249) cursor used by the Capability."""

    @property
    def description(self) -> Sequence[Sequence[Any]] | None:
        """Result columns; the first item of each entry is the column name."""
        ...

    @property
    def rowcount(self) -> int:
        """Rows affected by the last statement, or -1."""
        ...

    def execute(self, operation: str, parameters: Any = ..., /) -> object:  # noqa: ANN401
        """Run one statement."""
        ...

    def executemany(self, operation: str, seq_of_parameters: Any, /) -> object:  # noqa: ANN401
        """Run one statement for each parameter set."""
        ...

    def fetchall(self) -> Sequence[Sequence[Any]]:
        """Return the remaining rows."""
        ...

    def close(self) -> object:
        """Release the cursor."""
        ...


class DbapiConnection(Protocol):
    """Subset of a DB-API 2.0 connection used by the Capability."""

    def cursor(self) -> DbapiCursor:
        """Return a new cursor."""
        ...

    def close(self) -> object:
        """Close the connection."""
        ...


class SqlProvider(ABC):
    """Contract of a SQL Provider.

    A Provider knows one database engine and its driver. It must:

    * return connections in **autocommit** mode (the Capability issues the
      transaction statements itself);
    * declare the driver's DB-API :attr:`paramstyle`, so that portable
      ``:name`` placeholders can be translated;
    * translate driver exceptions into :class:`SqlError` subclasses, without
      parameter values or credentials in the messages;
    * never log or expose credentials (resolve them as secrets).

    Attributes:
        dialect: Name of the engine, such as ``"sqlite"`` or ``"postgresql"``.
        paramstyle: DB-API paramstyle of the driver.
    """

    dialect: ClassVar[str]
    paramstyle: ClassVar[str]

    @classmethod
    @abstractmethod
    def from_config(cls, section: ConfigSection) -> Self:
        """Create the Provider from the ``[capabilities.<name>]`` table (without ``provider``)."""

    def verify(self) -> None:  # noqa: B027 - optional hook with a no-op default
        """Check prerequisites; raise ``CapabilityUnavailableError`` if not met."""

    @abstractmethod
    def connect(self) -> DbapiConnection:
        """Open a connection in autocommit mode.

        Raises:
            SqlConnectionError: If the database cannot be reached.
        """

    @abstractmethod
    def is_driver_error(self, error: BaseException) -> bool:
        """Tell whether ``error`` comes from the driver and must be translated."""

    @abstractmethod
    def translate_error(self, error: BaseException) -> SqlError:
        """Translate a driver error into a :class:`SqlError`."""

    @abstractmethod
    def column_type(self, sql_type: SqlType) -> str:
        """Return the dialect type used for ``sql_type`` in DDL."""

    def adapt(self, value: object) -> object:
        """Convert a parameter value to a type the driver accepts (default: unchanged)."""
        return value

    def quote_identifier(self, name: str) -> str:
        """Quote an already validated identifier (default: ANSI double quotes)."""
        return '"' + name.replace('"', '""') + '"'

    def begin_statement(self) -> str:
        """Statement that opens a transaction."""
        return "BEGIN"

    def savepoint_statements(self, name: str) -> tuple[str, str, str]:
        """Statements to create, release and roll back to the savepoint ``name``."""
        return (
            f"SAVEPOINT {name}",
            f"RELEASE SAVEPOINT {name}",
            f"ROLLBACK TO SAVEPOINT {name}",
        )

    def describe(self) -> str:
        """Human-readable description for logs, without credentials."""
        return self.dialect
