"""The SQLite Provider passes the conformance suite of the SQL Capability (D-21)."""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from pathlib import Path

import pytest

from orchestrator_core import SecretRef, SecretResolver, SecretStore
from orchestrator_sql import SqlConnectionError, SqlProvider
from orchestrator_sql.testing import SqlProviderContract
from orchestrator_sqlite import SqliteProvider

PASSWORD = "S3NT1NEL-contract-password-c41d"


class TestSqliteContract(SqlProviderContract):
    def make_provider(self) -> SqlProvider:
        return SqliteProvider(self.temporary_directory() / "contract.db")


class Vault:
    """Test-only resolver standing in for a secret store."""

    def resolve(self, target: str) -> str:
        return {"db": PASSWORD}[target]


class PasswordSqliteProvider(SqliteProvider):
    """SQLite behind a password resolved by reference, as a server-based Provider would do."""

    def __init__(self, database: Path, password: SecretRef) -> None:
        super().__init__(database)
        self._password = password

    def connect(self, secrets: SecretStore) -> sqlite3.Connection:
        if secrets.resolve(self._password).reveal() != PASSWORD:
            msg = "login failed for the configured user"
            raise SqlConnectionError(msg)
        return super().connect(secrets)


class TestPasswordSqliteContract(SqlProviderContract):
    """The whole suite, with credentials resolved through ``secret_resolvers``."""

    def make_provider(self) -> SqlProvider:
        directory = self.temporary_directory()
        return PasswordSqliteProvider(directory / "contract.db", SecretRef.parse("vault:db"))

    def secret_resolvers(self) -> Mapping[str, SecretResolver]:
        return {"vault": Vault()}


def test_the_contract_detects_a_provider_that_keeps_the_password() -> None:
    class Hoarder(PasswordSqliteProvider):
        def connect(self, secrets: SecretStore) -> sqlite3.Connection:
            self.kept = secrets.resolve(self._password).reveal()
            return super().connect(secrets)

    class Contract(TestPasswordSqliteContract):
        def make_provider(self) -> SqlProvider:
            return Hoarder(self.temporary_directory() / "c.db", SecretRef.parse("vault:db"))

    contract = Contract()
    contract.setup_method()
    try:
        with pytest.raises(AssertionError, match="kept or exposed"):
            contract.test_credentials_are_not_kept_or_exposed()
    finally:
        contract.teardown_method()
