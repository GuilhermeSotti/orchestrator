from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

import sqlite3

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import Engine, Connection
except ImportError:  # pragma: no cover
    create_engine = None
    text = None
    Engine = Any
    Connection = Any


class SQLProviderError(RuntimeError):
    pass


@dataclass
class SQLProvider:
    connection: str | Any
    use_sqlalchemy: bool = True

    def __post_init__(self) -> None:
        self._engine: Engine | None = None
        self._connection_factory: Any | None = None
        self._is_sqlite = False

        if isinstance(self.connection, str):
            # Treat explicit sqlite URIs and the ':memory:' marker as SQLite
            is_sqlite_uri = self.connection == ":memory:" or str(self.connection).startswith("sqlite")
            if self.use_sqlalchemy and create_engine is not None and not is_sqlite_uri:
                self._engine = create_engine(self.connection, future=True)
                self._is_sqlite = False
            else:
                if self.connection == ":memory:":
                    self._sqlite_connection = sqlite3.connect(self.connection)
                    self._connection_factory = lambda: self._sqlite_connection
                else:
                    self._connection_factory = lambda: sqlite3.connect(self.connection)
                self._is_sqlite = True
        elif hasattr(self.connection, "execute"):
            self._connection_factory = lambda: self.connection
            self._is_sqlite = isinstance(self.connection, sqlite3.Connection)
        else:
            raise SQLProviderError("Unsupported connection type for SQLProvider")

    @property
    def dialect(self) -> str:
        if self._engine is not None and hasattr(self._engine, "dialect"):
            return getattr(self._engine.dialect, "name", "unknown")
        return "sqlite"

    @contextmanager
    def _connection_context(self):
        if self._engine is not None:
            with self._engine.begin() as conn:
                yield conn
        else:
            conn = self._connection_factory()
            try:
                yield conn
                conn.commit()
            finally:
                if conn is not getattr(self, "_sqlite_connection", None) and conn is not self.connection:
                    conn.close()

    def execute(self, query: str, parameters: dict[str, Any] | None = None, fetch: bool = False) -> list[dict[str, Any]] | None:
        if not query or not query.strip():
            raise SQLProviderError("SQL query must be a non-empty string")

        parameters = parameters or {}

        with self._connection_context() as conn:
            if self._engine is not None:
                result = conn.execute(text(query), parameters)
                if fetch:
                    return [dict(row) for row in result.mappings().all()]
                return None

            cursor = conn.cursor()
            try:
                cursor.execute(query, parameters)
            except sqlite3.Error as exc:
                raise SQLProviderError(str(exc)) from exc

            if fetch:
                columns = [column[0] for column in cursor.description or []]
                rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
                return rows
            return None

    def create_schema(self, schema_name: str) -> None:
        if not schema_name:
            return

        if self._is_sqlite:
            return

        qualified = self._quote_identifier(schema_name)
        if self.dialect == "mssql":
            query = f"IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = :schema) EXEC('CREATE SCHEMA {qualified}')"
            self.execute(query, {"schema": schema_name})
            return

        query = f"CREATE SCHEMA IF NOT EXISTS {qualified}"
        self.execute(query)

    def _quote_identifier(self, name: str) -> str:
        if self.dialect == "mssql":
            return f"[{name}]"
        return f'"{name}"'

    def _qualified_name(self, schema_name: str | None, table_name: str) -> str:
        table_name = self._quote_identifier(table_name)
        if not schema_name:
            return table_name

        if self._is_sqlite:
            clean_name = table_name.strip('"')
            return self._quote_identifier(f"{schema_name}_{clean_name}")

        return f"{self._quote_identifier(schema_name)}.{table_name}"

    def _build_column_definition(self, column: dict[str, Any]) -> str:
        name = self._quote_identifier(column["name"])
        column_type = column.get("type", "TEXT")
        if self._is_sqlite:
            normalized_type = column_type.upper()
            if normalized_type.startswith("VARCHAR"):
                column_type = "TEXT"
            elif normalized_type.startswith("DATETIME"):
                column_type = "TEXT"
            elif normalized_type in {"BIT", "SMALLINT", "BIGINT", "INT"}:
                column_type = "INTEGER"
        parts = [name, column_type]

        identity = column.get("identity", False)
        primary_key = column.get("primary_key", False)

        if identity and self._is_sqlite and primary_key:
            parts = [name, "INTEGER", "PRIMARY KEY", "AUTOINCREMENT"]
        elif identity and self.dialect == "mssql":
            parts.append("IDENTITY(1,1)")

        if not column.get("nullable", True):
            parts.append("NOT NULL")

        if "default" in column and column["default"] is not None:
            default_value = column["default"]
            if self._is_sqlite and isinstance(default_value, str):
                if "SYSUTCDATETIME" in default_value.upper() or "GETDATE" in default_value.upper():
                    default_value = "CURRENT_TIMESTAMP"
            parts.append(f"DEFAULT {default_value}")

        if primary_key and not (identity and self._is_sqlite):
            parts.append("PRIMARY KEY")

        if column.get("unique", False):
            parts.append("UNIQUE")

        return " ".join(parts)

    def _build_table_ddl(self, schema_name: str, table_def: dict[str, Any]) -> str:
        table_name = table_def["name"]
        qualified = self._qualified_name(schema_name, table_name)

        columns = [self._build_column_definition(column) for column in table_def.get("columns", [])]

        table_constraints: list[str] = []
        primary_key = table_def.get("primary_key")
        if primary_key and isinstance(primary_key, list):
            cols = ", ".join(self._quote_identifier(column) for column in primary_key)
            table_constraints.append(f"CONSTRAINT {self._quote_identifier('PK_' + table_name)} PRIMARY KEY ({cols})")

        for constraint in table_def.get("constraints", []):
            constraint_type = constraint.get("type")
            name = constraint.get("name")
            if constraint_type == "check":
                expression = constraint.get("expression")
                if name and expression:
                    table_constraints.append(f"CONSTRAINT {self._quote_identifier(name)} CHECK ({expression})")
            elif constraint_type == "foreign_key":
                key_columns = constraint.get("columns", [])
                referenced_table = constraint.get("referenced_table")
                referenced_columns = constraint.get("referenced_columns", [])
                if key_columns and referenced_table and referenced_columns:
                    if self._is_sqlite:
                        continue
                    cols = ", ".join(self._quote_identifier(col) for col in key_columns)
                    ref_cols = ", ".join(self._quote_identifier(col) for col in referenced_columns)
                    table_constraints.append(
                        f"CONSTRAINT {self._quote_identifier(name)} FOREIGN KEY ({cols}) REFERENCES {referenced_table} ({ref_cols})"
                    )

        definitions = columns + table_constraints
        body = ",\n    ".join(definitions)
        return f"CREATE TABLE {qualified} (\n    {body}\n)"

    def _create_indexes(self, schema_name: str, table_def: dict[str, Any]) -> None:
        if not table_def.get("indexes"):
            return

        qualified = self._qualified_name(schema_name, table_def["name"])
        for index in table_def.get("indexes", []):
            name = index.get("name") or f"IX_{table_def['name']}_{'_'.join(index.get('columns', []))}"
            columns = ", ".join(self._quote_identifier(column) for column in index.get("columns", []))
            unique = "UNIQUE " if index.get("unique") else ""
            if self._is_sqlite:
                self.execute(f"CREATE {unique}INDEX IF NOT EXISTS {self._quote_identifier(name)} ON {qualified} ({columns})")
            else:
                self.execute(f"CREATE {unique}INDEX {self._quote_identifier(name)} ON {qualified} ({columns})")

    def create_table(self, schema_name: str, table_def: dict[str, Any]) -> None:
        if not isinstance(table_def, dict) or "name" not in table_def:
            raise SQLProviderError("Table definition must be a mapping containing a name")

        self.create_schema(schema_name)
        ddl = self._build_table_ddl(schema_name, table_def)
        self.execute(ddl)
        self._create_indexes(schema_name, table_def)

    def insert(self, schema_name: str, table_name: str, data: dict[str, Any]) -> None:
        if not data:
            return

        qualified = self._qualified_name(schema_name, table_name)
        columns = ", ".join(self._quote_identifier(key) for key in data.keys())
        placeholders = ", ".join(f":{key}" for key in data.keys())
        sql = f"INSERT INTO {qualified} ({columns}) VALUES ({placeholders})"
        self.execute(sql, data)

    def select(self, schema_name: str, table_name: str, query: str = "*", parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        qualified = self._qualified_name(schema_name, table_name)
        if query.strip().lower().startswith("select"):
            sql = query
        else:
            sql = f"SELECT {query} FROM {qualified}"
        return self.execute(sql, parameters, fetch=True) or []

    def update(self, schema_name: str, table_name: str, data: dict[str, Any], where: str, parameters: dict[str, Any] | None = None) -> None:
        if not data:
            return

        qualified = self._qualified_name(schema_name, table_name)
        set_clause = ", ".join(f"{self._quote_identifier(key)} = :{key}" for key in data.keys())
        payload = {**data, **(parameters or {})}
        sql = f"UPDATE {qualified} SET {set_clause} WHERE {where}"
        self.execute(sql, payload)

    def delete(self, schema_name: str, table_name: str, where: str, parameters: dict[str, Any] | None = None) -> None:
        qualified = self._qualified_name(schema_name, table_name)
        sql = f"DELETE FROM {qualified} WHERE {where}"
        self.execute(sql, parameters)
