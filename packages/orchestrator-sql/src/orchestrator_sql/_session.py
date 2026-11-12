"""SqlSession: the execution-scoped handle of the SQL Capability."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from typing import Any

from orchestrator_core import ExecutionOutcome
from orchestrator_sql._errors import SqlError, SqlProgrammingError
from orchestrator_sql._identifiers import TableName, validate_identifier
from orchestrator_sql._params import placeholder_names, translate
from orchestrator_sql._provider import DbapiConnection, DbapiCursor, SqlProvider
from orchestrator_sql._schema import Table

_logger = logging.getLogger("orchestrator_sql")
_SQL_PREVIEW = 160


class Row(Mapping[str, Any]):
    """Immutable result row, accessed by column name.

    Example:
        >>> row = Row(("id", "name"), (1, "Ana"))
        >>> row["name"], dict(row)
        ('Ana', {'id': 1, 'name': 'Ana'})
    """

    __slots__ = ("_columns", "_values")

    def __init__(self, columns: tuple[str, ...], values: Sequence[Any]) -> None:
        """Create a row from column names and values of the same length."""
        self._columns = columns
        self._values = tuple(values)

    def __getitem__(self, key: str) -> Any:  # noqa: ANN401 - column values have any type
        """Return the value of column ``key``."""
        try:
            return self._values[self._columns.index(key)]
        except ValueError:
            raise KeyError(key) from None

    def __iter__(self) -> Iterator[str]:
        """Iterate over column names."""
        return iter(self._columns)

    def __len__(self) -> int:
        """Return the number of columns."""
        return len(self._columns)

    def as_tuple(self) -> tuple[Any, ...]:
        """Return the values in column order."""
        return self._values

    def __repr__(self) -> str:
        """Return the row as a dictionary representation."""
        return f"Row({dict(self)!r})"


class SqlSession:
    """Database access of one execution: parameterized statements, transactions and helpers.

    Values always travel as parameters, written as ``:name``. Table and column
    names given to the helpers are validated and quoted. Statements run in
    autocommit mode unless they are inside :meth:`transaction`. A session is
    not thread-safe.
    """

    def __init__(self, provider: SqlProvider, connection: DbapiConnection) -> None:
        """Wrap an open connection. Sessions are created by ``SqlCapability``."""
        self._provider = provider
        self._connection: DbapiConnection | None = connection
        self._depth = 0

    @property
    def dialect(self) -> str:
        """Dialect of the Provider, such as ``"sqlite"``."""
        return self._provider.dialect

    @property
    def in_transaction(self) -> bool:
        """Whether a transaction opened by :meth:`transaction` is active."""
        return self._depth > 0

    @property
    def closed(self) -> bool:
        """Whether the connection was closed."""
        return self._connection is None

    def quote(self, name: str | TableName) -> str:
        """Validate and quote a table (``schema.table``) or column name for custom SQL."""
        if isinstance(name, TableName) or "." in name:
            table = TableName.parse(name)
            quoted = self._provider.quote_identifier(table.name)
            if table.schema is None:
                return quoted
            return f"{self._provider.quote_identifier(table.schema)}.{quoted}"
        return self._provider.quote_identifier(validate_identifier(name))

    # Statements -------------------------------------------------------------

    def execute(self, sql: str, params: Mapping[str, object] | None = None) -> int:
        """Run one statement and return the number of affected rows (-1 if unknown)."""
        with self._cursor() as cursor:
            self._run(cursor, sql, params)
            return cursor.rowcount

    def execute_many(self, sql: str, rows: Iterable[Mapping[str, object]]) -> int:
        """Run one statement for each parameter set; return the affected rows (-1 if unknown)."""
        batch = [dict(row) for row in rows]
        if not batch:
            return 0
        names = set(placeholder_names(sql))
        translated_sql = ""
        values: list[object] = []
        for index, row in enumerate(batch):
            if set(row) != names:
                msg = f"parameter set {index} does not match the placeholders of the statement"
                raise SqlProgrammingError(msg)
            translated_sql, translated = translate(sql, self._adapt(row), self._provider.paramstyle)
            values.append(translated)
        _logger.debug("executemany (%d rows): %s", len(batch), _preview(sql))
        with self._cursor() as cursor:
            self._call(cursor.executemany, translated_sql, values)
            return cursor.rowcount

    def fetch_all(self, sql: str, params: Mapping[str, object] | None = None) -> list[Row]:
        """Run a query and return every row."""
        with self._cursor() as cursor:
            self._run(cursor, sql, params)
            columns = _columns(cursor)
            rows = self._call(cursor.fetchall)
        return [Row(columns, row) for row in rows]

    def fetch_one(self, sql: str, params: Mapping[str, object] | None = None) -> Row | None:
        """Run a query and return its only row, or ``None``.

        Raises:
            SqlProgrammingError: If the query returns more than one row.
        """
        rows = self.fetch_all(sql, params)
        if len(rows) > 1:
            msg = f"expected at most one row, got {len(rows)}"
            raise SqlProgrammingError(msg)
        return rows[0] if rows else None

    def scalar(self, sql: str, params: Mapping[str, object] | None = None) -> Any:  # noqa: ANN401
        """Return the first column of the only row, or ``None`` without rows."""
        row = self.fetch_one(sql, params)
        return None if row is None else row.as_tuple()[0]

    # Transactions -----------------------------------------------------------

    @contextmanager
    def transaction(self) -> Iterator[SqlSession]:
        """Group statements atomically: commit on success, roll back on error.

        Nested calls use savepoints.
        """
        savepoint = None if self._depth == 0 else f"orchestrator_sp_{self._depth}"
        if savepoint is None:
            self._raw(self._provider.begin_statement())
        else:
            self._raw(self._provider.savepoint_statements(savepoint)[0])
        self._depth += 1
        try:
            yield self
        except BaseException:
            self._end(savepoint, commit=False)
            raise
        self._end(savepoint, commit=True)

    def _end(self, savepoint: str | None, *, commit: bool) -> None:
        if self._depth == 0 or self._connection is None:
            return  # already rolled back by finalize, or the session is closed
        self._depth -= 1
        if savepoint is None:
            statement = "COMMIT" if commit else "ROLLBACK"
        else:
            _create, release, rollback = self._provider.savepoint_statements(savepoint)
            statement = release if commit else rollback
        if commit:
            self._raw(statement)
            return
        try:
            self._raw(statement)
        except Exception:  # never mask the error that caused the rollback
            _logger.warning("rollback failed", exc_info=True)

    # Helpers ----------------------------------------------------------------

    def create_table(self, table: Table, *, if_not_exists: bool = True) -> None:
        """Create ``table`` from its definition."""
        columns = []
        for column in table.columns:
            parts = [self.quote(column.name), self._provider.column_type(column.type)]
            if column.primary_key:
                parts.append("PRIMARY KEY")
            if not column.nullable and not column.primary_key:
                parts.append("NOT NULL")
            if column.unique:
                parts.append("UNIQUE")
            columns.append(" ".join(parts))
        guard = "IF NOT EXISTS " if if_not_exists else ""
        self.execute(f"CREATE TABLE {guard}{self.quote(table.name)} ({', '.join(columns)})")

    def drop_table(self, table: str | TableName, *, if_exists: bool = True) -> None:
        """Drop ``table``."""
        guard = "IF EXISTS " if if_exists else ""
        self.execute(f"DROP TABLE {guard}{self.quote(table)}")

    def insert(self, table: str | TableName, row: Mapping[str, object]) -> int:
        """Insert one row; keys are column names."""
        return self.insert_many(table, [row])

    def insert_many(self, table: str | TableName, rows: Sequence[Mapping[str, object]]) -> int:
        """Insert rows that share the same columns; return the number of rows inserted."""
        if not rows:
            return 0
        columns = list(rows[0])
        if not columns:
            msg = "rows must have at least one column"
            raise SqlProgrammingError(msg)
        names = [validate_identifier(column) for column in columns]
        placeholders = {name: f"c{index}" for index, name in enumerate(names)}
        sql = (
            f"INSERT INTO {self.quote(table)} ({', '.join(self.quote(n) for n in names)}) "  # noqa: S608 - quoted, validated identifiers; values are parameters
            f"VALUES ({', '.join(':' + placeholders[n] for n in names)})"
        )
        batch = []
        for index, row in enumerate(rows):
            if list(row) != columns:
                msg = f"row {index} does not have the same columns, in the same order, as row 0"
                raise SqlProgrammingError(msg)
            batch.append({placeholders[name]: row[name] for name in names})
        self.execute_many(sql, batch)
        return len(batch)

    def select(
        self,
        table: str | TableName,
        *,
        columns: Sequence[str] | None = None,
        where: Mapping[str, object] | None = None,
        order_by: Sequence[str] = (),
    ) -> list[Row]:
        """Select rows whose columns equal the values in ``where`` (all of them)."""
        selected = "*" if not columns else ", ".join(self.quote(c) for c in columns)
        clause, params = self._where(where or {}, prefix="w")
        order = f" ORDER BY {', '.join(self.quote(c) for c in order_by)}" if order_by else ""
        return self.fetch_all(f"SELECT {selected} FROM {self.quote(table)}{clause}{order}", params)  # noqa: S608 - quoted, validated identifiers; values are parameters

    def update(
        self,
        table: str | TableName,
        values: Mapping[str, object],
        *,
        where: Mapping[str, object],
    ) -> int:
        """Update rows matching ``where`` (required, to avoid updating the whole table)."""
        if not values:
            msg = "nothing to update"
            raise SqlProgrammingError(msg)
        if not where:
            msg = "update requires a non-empty where; use execute() for bulk updates"
            raise SqlProgrammingError(msg)
        assignments = {f"v{index}": name for index, name in enumerate(values)}
        set_clause = ", ".join(f"{self.quote(name)} = :{key}" for key, name in assignments.items())
        params = {key: values[name] for key, name in assignments.items()}
        clause, where_params = self._where(where, prefix="w")
        return self.execute(
            f"UPDATE {self.quote(table)} SET {set_clause}{clause}",  # noqa: S608 - quoted, validated identifiers; values are parameters
            params | where_params,
        )

    def delete(self, table: str | TableName, *, where: Mapping[str, object]) -> int:
        """Delete rows matching ``where`` (required, to avoid emptying the table)."""
        if not where:
            msg = "delete requires a non-empty where; use execute() for bulk deletes"
            raise SqlProgrammingError(msg)
        clause, params = self._where(where, prefix="w")
        return self.execute(f"DELETE FROM {self.quote(table)}{clause}", params)  # noqa: S608 - quoted, validated identifiers; values are parameters

    # Lifecycle (called by the Capability) ------------------------------------

    def finalize(self, outcome: ExecutionOutcome | None) -> None:  # noqa: ARG002 - Finalizer signature
        """Roll back a transaction left open by the automation."""
        if self._depth and self._connection is not None:
            _logger.warning("rolling back a transaction left open by the automation")
            self._depth = 0
            self._raw("ROLLBACK")

    def close(self) -> None:
        """Close the connection. Idempotent."""
        connection, self._connection = self._connection, None
        if connection is not None:
            self._call(connection.close)

    # Internals --------------------------------------------------------------

    def _where(self, where: Mapping[str, object], *, prefix: str) -> tuple[str, dict[str, object]]:
        if not where:
            return "", {}
        conditions = []
        params: dict[str, object] = {}
        for index, (column, value) in enumerate(where.items()):
            key = f"{prefix}{index}"
            if value is None:
                conditions.append(f"{self.quote(column)} IS NULL")
            else:
                conditions.append(f"{self.quote(column)} = :{key}")
                params[key] = value
        return " WHERE " + " AND ".join(conditions), params

    def _adapt(self, params: Mapping[str, object]) -> dict[str, object]:
        return {name: self._provider.adapt(value) for name, value in params.items()}

    def _run(self, cursor: DbapiCursor, sql: str, params: Mapping[str, object] | None) -> None:
        translated_sql, values = translate(
            sql, self._adapt(params or {}), self._provider.paramstyle
        )
        _logger.debug("execute: %s params=%s", _preview(sql), sorted(params or {}))
        self._call(cursor.execute, translated_sql, values)

    def _raw(self, sql: str) -> None:
        with self._cursor() as cursor:
            _logger.debug("execute: %s", sql)
            self._call(cursor.execute, sql)

    @contextmanager
    def _cursor(self) -> Iterator[DbapiCursor]:
        if self._connection is None:
            msg = "the SQL session is closed"
            raise SqlProgrammingError(msg)
        cursor = self._call(self._connection.cursor)
        try:
            yield cursor
        finally:
            self._call(cursor.close)

    def _call[**P, R](self, function: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return function(*args, **kwargs)
        except SqlError:
            raise
        except Exception as exc:
            if self._provider.is_driver_error(exc):
                raise self._provider.translate_error(exc) from exc
            raise


def _columns(cursor: DbapiCursor) -> tuple[str, ...]:
    description = cursor.description or ()
    columns = tuple(str(column[0]) for column in description)
    if len(set(columns)) != len(columns):
        msg = "the query returns duplicate column names; use aliases"
        raise SqlProgrammingError(msg)
    return columns


def _preview(sql: str) -> str:
    text = " ".join(sql.split())
    return text if len(text) <= _SQL_PREVIEW else text[:_SQL_PREVIEW] + "…"
