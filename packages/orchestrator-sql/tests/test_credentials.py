"""Credentials through the port (RFC-0006, 2.1, option A): connect(secrets) and the sentinel."""

from __future__ import annotations

import io
import json
import logging
import sqlite3
from collections.abc import Mapping
from typing import ClassVar, Self

from orchestrator_core import (
    ConfigSection,
    Event,
    ExecutionContext,
    ExecutionStatus,
    RuntimeBuilder,
    SecretRef,
    SecretStore,
)
from orchestrator_core.logs import configure_logging
from orchestrator_core.testing import EventRecorder, InMemoryRecordSink
from orchestrator_sql import SqlCapability, SqlConnectionError

from .conftest import StdlibSqlite

SENTINEL = "S3NT1NEL-db-password-5e0b"


class Vault:
    """Test-only resolver: the "vault" holds the database password."""

    def __init__(self, secrets: Mapping[str, str]) -> None:
        self._secrets = dict(secrets)

    def resolve(self, target: str) -> str:
        return self._secrets[target]


class PasswordSqlite(StdlibSqlite):
    """Provider whose "server" accepts one password, read by reference.

    ``leaky_driver`` simulates a driver whose error message repeats the password.
    """

    accepted: ClassVar[str] = SENTINEL

    def __init__(self, password: SecretRef, *, leaky_driver: bool = False) -> None:
        super().__init__(":memory:")
        self._password = password
        self._leaky_driver = leaky_driver

    @classmethod
    def from_config(cls, section: ConfigSection) -> Self:
        section.check_keys(("password", "leaky_driver"))
        return cls(
            section.get_secret_ref("password"),
            leaky_driver=section.get_bool("leaky_driver", False),
        )

    def connect(self, secrets: SecretStore) -> sqlite3.Connection:
        password = secrets.resolve(self._password).reveal()
        if self._leaky_driver:
            error = sqlite3.OperationalError(f"login failed with password {password}")
            raise SqlConnectionError(str(error)) from error
        if password != self.accepted:
            msg = "login failed for the configured user"
            raise SqlConnectionError(msg)
        return super().connect(secrets)

    def describe(self) -> str:
        return f"password-sqlite (password from {self._password.scheme}:)"


def runtime_for(provider_settings: Mapping[str, object]) -> tuple[RuntimeBuilder, EventRecorder]:
    events = EventRecorder()
    builder = (
        RuntimeBuilder()
        .with_environment({}, prefix=None)
        .with_secret_resolver("vault", Vault({"db": SENTINEL, "wrong": "not-the-password"}))
        .with_settings({"capabilities": {"sql": {"provider": "pwd", **provider_settings}}})
        .with_capability(SqlCapability, providers={"pwd": PasswordSqlite})
        .on_event(Event, events)
    )
    return builder, events


def test_the_capability_hands_the_execution_secrets_to_the_provider() -> None:
    builder, _ = runtime_for({"password": "vault:db"})

    def automation(ctx: ExecutionContext) -> object:
        return ctx.capability(SqlCapability).scalar("SELECT 41 + 1")

    result = builder.build().run(automation)
    assert result.succeeded, result.error
    assert result.output == 42


def test_a_wrong_password_fails_provisioning_without_the_value() -> None:
    builder, _ = runtime_for({"password": "vault:wrong"})
    result = builder.build().run(lambda ctx: None)
    assert result.status is ExecutionStatus.FAILED
    assert result.stage("provision_dependencies").status.value == "failed"
    assert "not-the-password" not in json.dumps(result.record.to_dict())


def test_the_password_never_reaches_logs_events_records_or_the_provider() -> None:
    """E7.8 acceptance: even a driver message with the password is masked."""
    stream = io.StringIO()
    handler = configure_logging(
        "DEBUG", stream=stream, logger="orchestrator_core", json_output=True
    )
    sink = InMemoryRecordSink()
    builder, events = runtime_for({"password": "vault:db", "leaky_driver": True})
    runtime = builder.with_record_sink(sink).build()
    try:
        result = runtime.run(lambda ctx: None)
    finally:
        logging.getLogger("orchestrator_core").removeHandler(handler)
    assert result.status is ExecutionStatus.FAILED
    assert SENTINEL in str(result.error)  # the raw exception keeps it, for programmatic use
    texts = [
        stream.getvalue(),
        json.dumps(result.record.to_dict()),
        json.dumps([record.to_dict() for record in sink.records]),
        repr(events.events),
        repr(result),
    ]
    for text in texts:
        assert SENTINEL not in text
    assert "login failed with password ***" in json.dumps(result.record.to_dict())
    provider = PasswordSqlite(SecretRef.parse("vault:db"))
    assert SENTINEL not in provider.describe()
    assert SENTINEL not in repr(vars(provider))
