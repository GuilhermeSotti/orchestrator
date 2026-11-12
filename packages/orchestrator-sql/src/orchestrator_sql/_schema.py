"""Portable column types and table definitions for simple DDL."""

from __future__ import annotations

import enum
from collections.abc import Sequence
from dataclasses import dataclass

from orchestrator_sql._errors import SqlProgrammingError
from orchestrator_sql._identifiers import TableName, validate_identifier


class SqlType(enum.StrEnum):
    """Portable column types; each Provider maps them to its dialect."""

    TEXT = "text"
    INTEGER = "integer"
    BIGINT = "bigint"
    REAL = "real"
    NUMERIC = "numeric"
    BOOLEAN = "boolean"
    DATE = "date"
    TIMESTAMP = "timestamp"
    BLOB = "blob"


@dataclass(frozen=True, slots=True)
class Column:
    """Column of a :class:`Table`.

    Defaults are deliberately not supported: they would require rendering
    literal values into DDL.
    """

    name: str
    type: SqlType
    nullable: bool = True
    primary_key: bool = False
    unique: bool = False

    def __post_init__(self) -> None:
        """Validate the column name."""
        validate_identifier(self.name)


@dataclass(frozen=True, slots=True)
class Table:
    """Table definition used by :meth:`SqlSession.create_table`.

    Example:
        >>> table = Table.define("orders", [Column("id", SqlType.INTEGER, primary_key=True)])
        >>> table.name, table.column_names
        (TableName(name='orders', schema=None), ('id',))
    """

    name: TableName
    columns: tuple[Column, ...]

    def __post_init__(self) -> None:
        """Validate the definition."""
        if not self.columns:
            msg = f"table {self.name} has no columns"
            raise SqlProgrammingError(msg)
        names = [column.name.lower() for column in self.columns]
        if len(set(names)) != len(names):
            msg = f"table {self.name} has duplicate column names"
            raise SqlProgrammingError(msg)

    @classmethod
    def define(cls, name: str | TableName, columns: Sequence[Column]) -> Table:
        """Create a table definition from a name and columns."""
        return cls(TableName.parse(name), tuple(columns))

    @property
    def column_names(self) -> tuple[str, ...]:
        """Column names, in order."""
        return tuple(column.name for column in self.columns)
