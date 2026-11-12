"""The SQLite Provider passes the conformance suite of the SQL Capability (D-21)."""

from __future__ import annotations

from orchestrator_sql import SqlProvider
from orchestrator_sql.testing import SqlProviderContract
from orchestrator_sqlite import SqliteProvider


class TestSqliteContract(SqlProviderContract):
    def make_provider(self) -> SqlProvider:
        return SqliteProvider(self.temporary_directory() / "contract.db")
