from __future__ import annotations

import logging
from pathlib import Path
from types import SimpleNamespace

import pytest

from orchestrator_core import (
    ConfigurationError,
    ExecutionContext,
    ExecutionStatus,
    RuntimeBuilder,
    StageStatus,
)
from orchestrator_sql import (
    Row,
    SqlCapability,
    SqlError,
    SqlIntegrityError,
    SqlProgrammingError,
    SqlSession,
)


def test_statements_and_helpers(session: SqlSession) -> None:
    rows = [
        {"id": 1, "name": "Ana", "email": "ana@example.com", "team": "a"},
        {"id": 2, "name": "Bia", "email": "bia@example.com", "team": None},
    ]
    assert session.insert_many("people", rows) == 2
    assert session.insert_many("people", []) == 0
    assert session.execute_many("UPDATE people SET team = :t WHERE id = :i", []) == 0
    assert session.scalar("SELECT count(*) FROM people WHERE team = :t", {"t": "a"}) == 1
    assert session.select("people", columns=["name"], where={"team": None})[0]["name"] == "Bia"
    assert session.fetch_one("SELECT name FROM people WHERE id = :id", {"id": 9}) is None
    assert session.scalar("SELECT name FROM people WHERE id = :id", {"id": 9}) is None
    assert session.update("people", {"team": "b"}, where={"id": 2}) == 1
    assert session.delete("people", where={"id": 1}) == 1
    (row,) = session.select("people")
    assert isinstance(row, Row)
    assert dict(row) == {
        "id": 2,
        "name": "Bia",
        "email": "bia@example.com",
        "team": "b",
    }
    assert repr(row).startswith("Row(")
    with pytest.raises(KeyError):
        row["missing"]
    session.drop_table("people")
    session.drop_table("people")  # IF EXISTS by default


def test_helpers_refuse_unsafe_or_ambiguous_calls(session: SqlSession) -> None:
    with pytest.raises(SqlProgrammingError, match="requires a non-empty where"):
        session.update("people", {"team": "x"}, where={})
    with pytest.raises(SqlProgrammingError, match="requires a non-empty where"):
        session.delete("people", where={})
    with pytest.raises(SqlProgrammingError, match="nothing to update"):
        session.update("people", {}, where={"id": 1})
    with pytest.raises(SqlProgrammingError, match="invalid SQL identifier"):
        session.select("people; DROP TABLE people")
    with pytest.raises(SqlProgrammingError, match="invalid SQL identifier"):
        session.insert("people", {"id": 1, "name) VALUES (1); --": "x"})
    with pytest.raises(SqlProgrammingError, match="same columns"):
        session.insert_many("people", [{"id": 1, "name": "a"}, {"name": "b", "id": 2}])
    with pytest.raises(SqlProgrammingError, match="at least one column"):
        session.insert("people", {})
    with pytest.raises(SqlProgrammingError, match="does not match the placeholders"):
        session.execute_many("INSERT INTO people (id, name) VALUES (:id, :name)", [{"id": 1}])
    session.insert_many("people", [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}])
    with pytest.raises(SqlProgrammingError, match="at most one row"):
        session.fetch_one("SELECT id FROM people")
    with pytest.raises(SqlProgrammingError, match="duplicate column names"):
        session.fetch_all("SELECT id, id FROM people")


def test_driver_errors_are_translated_and_chained(session: SqlSession) -> None:
    session.insert("people", {"id": 1, "name": "Ana"})
    with pytest.raises(SqlIntegrityError) as info:
        session.insert("people", {"id": 1, "name": "again"})
    assert info.value.__cause__ is not None
    with pytest.raises(SqlError):
        session.execute("SELEKT 1")


def test_transactions_and_finalize(session: SqlSession) -> None:
    with session.transaction():
        session.insert("people", {"id": 1, "name": "kept"})
        assert session.in_transaction
    with pytest.raises(ZeroDivisionError), session.transaction():
        session.insert("people", {"id": 2, "name": "gone"})
        _ = 1 / 0
    with session.transaction():
        session.insert("people", {"id": 3, "name": "outer"})
        with pytest.raises(KeyError), session.transaction():
            session.insert("people", {"id": 4, "name": "inner"})
            raise KeyError
    open_transaction = session.transaction()
    open_transaction.__enter__()
    session.insert("people", {"id": 5, "name": "never committed"})
    session.finalize(None)
    assert not session.in_transaction
    assert [r["id"] for r in session.select("people", columns=["id"], order_by=["id"])] == [1, 3]


def test_rollback_failure_does_not_mask_the_original_error(
    fakes: SimpleNamespace,
) -> None:
    provider = fakes.StdlibSqlite()
    session = SqlSession(provider, provider.connect())
    with pytest.raises(RuntimeError, match="original"), session.transaction():
        session.close()  # the rollback will fail: the session is closed
        raise RuntimeError("original")
    assert session.closed


def test_closed_session_and_quoting(fakes: SimpleNamespace) -> None:
    provider = fakes.StdlibSqlite()
    session = SqlSession(provider, provider.connect())
    assert session.quote("sales.orders") == '"sales"."orders"'
    assert session.quote("orders") == '"orders"'
    assert session.dialect == "sqlite"
    session.close()
    session.close()
    with pytest.raises(SqlProgrammingError, match="session is closed"):
        session.execute("SELECT 1")


@pytest.mark.parametrize(
    ("style", "expected"),
    [
        ("format", ('SELECT * FROM "people" WHERE "name" = %s', ("Ana",))),
        ("pyformat", ('SELECT * FROM "people" WHERE "name" = %(w0)s', {"w0": "Ana"})),
        ("numeric", ('SELECT * FROM "people" WHERE "name" = :1', ("Ana",))),
    ],
)
def test_helpers_produce_the_driver_paramstyle(
    style: str, expected: tuple[str, object], fakes: SimpleNamespace
) -> None:
    provider = fakes.recording_provider(style)()
    connection = provider.connect()
    session = SqlSession(provider, connection)  # type: ignore[arg-type]
    session.select("people", where={"name": "Ana"})
    assert connection.log == [expected]  # type: ignore[attr-defined]


def test_capability_selects_the_provider_by_configuration(
    tmp_path: Path, fakes: SimpleNamespace
) -> None:
    database = tmp_path / "app.db"
    runtime = (
        RuntimeBuilder()
        .with_environment(
            {
                "ORCHESTRATOR_CAPABILITIES__SQL__PROVIDER": "stdlib",
                "ORCHESTRATOR_CAPABILITIES__SQL__DATABASE": str(database),
            }
        )
        .with_capability(
            SqlCapability,
            providers={"stdlib": fakes.StdlibSqlite, "qmark": fakes.QmarkSqlite},
        )
        .build()
    )

    def automation(ctx: ExecutionContext) -> object:
        sql = ctx.capability(SqlCapability)
        sql.create_table(fakes.PEOPLE)
        sql.insert("people", {"id": 1, "name": "Ana"})
        return sql.scalar("SELECT name FROM people")

    result = runtime.run(automation)
    assert result.output == "Ana"
    assert database.exists()


def test_capability_configuration_errors(fakes: SimpleNamespace) -> None:
    providers = {"stdlib": fakes.StdlibSqlite}
    base = RuntimeBuilder().with_environment({}, prefix=None)
    with pytest.raises(ConfigurationError, match=r"capabilities\.sql\.provider: required key"):
        base.with_capability(SqlCapability, providers=providers).build()
    with pytest.raises(ConfigurationError, match="expected one of: stdlib"):
        RuntimeBuilder().with_environment({}, prefix=None).with_settings(
            {"capabilities": {"sql": {"provider": "oracle"}}}
        ).with_capability(SqlCapability, providers=providers).build()
    with pytest.raises(ConfigurationError, match=r"capabilities\.sql: unknown key\(s\): databse"):
        RuntimeBuilder().with_environment({}, prefix=None).with_settings(
            {"capabilities": {"sql": {"provider": "stdlib", "databse": "x"}}}
        ).with_capability(SqlCapability, providers=providers).build()


def test_failed_connection_fails_provisioning(
    caplog: pytest.LogCaptureFixture, fakes: SimpleNamespace
) -> None:
    class Unreachable(fakes.StdlibSqlite):  # type: ignore[name-defined,misc]
        def connect(self) -> object:  # type: ignore[override]
            raise SqlError("connection refused", retryable=True)

    runtime = (
        RuntimeBuilder()
        .with_environment({}, prefix=None)
        .with_capability(SqlCapability(Unreachable()))
        .build()
    )
    with caplog.at_level(logging.ERROR):
        result = runtime.run(lambda ctx: None)
    assert result.status is ExecutionStatus.FAILED
    assert result.stage("provision_dependencies").status is StageStatus.FAILED
    assert isinstance(result.error, SqlError)
    assert result.error.retryable
    assert SqlCapability(fakes.StdlibSqlite()).provider.dialect == "sqlite"
