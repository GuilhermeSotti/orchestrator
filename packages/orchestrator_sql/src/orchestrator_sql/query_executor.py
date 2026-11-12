from __future__ import annotations

from typing import Any

from .sql_provider import SQLProvider


class QueryExecutor:
    def __init__(self, provider: SQLProvider) -> None:
        self.provider = provider

    def execute_query(self, sql: str, parameters: dict[str, Any] | None = None) -> None:
        self.provider.execute(sql, parameters)

    def fetch_all(self, sql: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return self.provider.execute(sql, parameters, fetch=True) or []

    def fetch_one(self, sql: str, parameters: dict[str, Any] | None = None) -> dict[str, Any] | None:
        rows = self.fetch_all(sql, parameters)
        return rows[0] if rows else None

    def select(self, schema_name: str, table_name: str, query: str = "*", parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return self.provider.select(schema_name, table_name, query, parameters)
