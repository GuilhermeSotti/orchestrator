"""Conformance suite that every SQL Provider must pass (D-21).

Subclass :class:`SqlProviderContract` in the Provider's tests and implement
:meth:`~SqlProviderContract.make_provider`; pytest collects the inherited
``test_*`` methods. Nothing here imports pytest.

Example::

    class TestSqliteContract(SqlProviderContract):
        def make_provider(self) -> SqlProvider:
            return SqliteProvider(self.temporary_directory() / "contract.db")
"""

from __future__ import annotations

import shutil
import tempfile
from abc import ABC, abstractmethod
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from orchestrator_core import ExecutionContext, RuntimeBuilder
from orchestrator_core.testing import check_capability_conformance
from orchestrator_sql._capability import SqlCapability
from orchestrator_sql._errors import SqlIntegrityError, SqlProgrammingError
from orchestrator_sql._provider import SqlProvider
from orchestrator_sql._schema import Column, SqlType, Table
from orchestrator_sql._session import SqlSession

__all__ = ["SqlProviderContract"]

_ORDERS = Table.define(
    "order",  # reserved word on purpose: identifiers must be quoted
    [
        Column("id", SqlType.INTEGER, primary_key=True),
        Column("customer", SqlType.TEXT, nullable=False),
        Column("amount", SqlType.NUMERIC),
        Column("paid", SqlType.BOOLEAN),
        Column("due", SqlType.DATE),
        Column("created", SqlType.TIMESTAMP),
        Column("weight", SqlType.REAL),
        Column("big", SqlType.BIGINT),
        Column("raw", SqlType.BLOB),
        Column("code", SqlType.TEXT, unique=True),
    ],
)


class SqlProviderContract(ABC):
    """Behavior every :class:`SqlProvider` must show, as inheritable tests."""

    _directories: list[Path]

    @abstractmethod
    def make_provider(self) -> SqlProvider:
        """Return a fresh Provider pointing to an empty database."""

    def temporary_directory(self) -> Path:
        """Return a directory removed after the test (see :meth:`teardown_method`)."""
        directory = Path(tempfile.mkdtemp(prefix="orchestrator-sql-contract-"))
        self._directories.append(directory)
        return directory

    def setup_method(self) -> None:
        """Prepare per-test state (called by pytest)."""
        self._directories = []

    def teardown_method(self) -> None:
        """Remove temporary directories (called by pytest)."""
        for directory in self._directories:
            shutil.rmtree(directory, ignore_errors=True)

    def session(self) -> SqlSession:
        """Open a session outside of a Runtime (closed by the caller)."""
        provider = self.make_provider()
        provider.verify()
        return SqlSession(provider, provider.connect())

    # Contract -----------------------------------------------------------------

    def test_paramstyle_is_known(self) -> None:
        """The Provider declares a DB-API paramstyle supported by the Capability."""
        from orchestrator_sql._params import PARAMSTYLES  # noqa: PLC0415

        assert self.make_provider().paramstyle in PARAMSTYLES  # noqa: S101

    def test_named_parameters_and_scalar(self) -> None:
        """Portable ``:name`` placeholders work, including repeated names."""
        session = self.session()
        try:
            assert session.scalar("SELECT :a + :b + :a", {"a": 1, "b": 40}) == 42  # noqa: S101
        finally:
            session.close()

    def test_roundtrip_of_portable_types_with_reserved_table_name(self) -> None:
        """Every SqlType can be created, written and read back."""
        session = self.session()
        try:
            session.create_table(_ORDERS)
            session.insert(
                "order",
                {
                    "id": 1,
                    "customer": "Ana",
                    "amount": Decimal("10.50"),
                    "paid": True,
                    "due": date(2026, 11, 12),
                    "created": datetime(2026, 11, 12, 14, 30),  # noqa: DTZ001 - naive on purpose
                    "weight": 1.5,
                    "big": 2**40,
                    "raw": b"\x00\x01",
                    "code": "A-1",
                },
            )
            row = session.select("order", where={"id": 1})[0]
            assert row["customer"] == "Ana"  # noqa: S101
            assert row["weight"] == 1.5  # noqa: S101
            assert row["big"] == 2**40  # noqa: S101
            assert bytes(row["raw"]) == b"\x00\x01"  # noqa: S101
            assert str(row["due"]).startswith("2026-11-12")  # noqa: S101
            assert Decimal(str(row["amount"])) == Decimal("10.50")  # noqa: S101
            assert bool(row["paid"]) is True  # noqa: S101
        finally:
            session.close()

    def test_crud_helpers(self) -> None:
        """insert_many, select, update and delete build safe, parameterized SQL."""
        session = self.session()
        try:
            session.create_table(_ORDERS)
            rows = [{"id": n, "customer": f"c{n}", "code": f"K{n}"} for n in range(1, 6)]
            assert session.insert_many("order", rows) == 5  # noqa: S101
            assert session.update("order", {"customer": "x"}, where={"id": 2}) == 1  # noqa: S101
            assert session.delete("order", where={"id": 5}) == 1  # noqa: S101
            selected = session.select("order", columns=["id", "customer"], order_by=["id"])
            assert [tuple(r.values()) for r in selected] == [  # noqa: S101
                (1, "c1"),
                (2, "x"),
                (3, "c3"),
                (4, "c4"),
            ]
            assert session.select("order", where={"amount": None}, columns=["id"])  # noqa: S101
        finally:
            session.close()

    def test_transactions_commit_roll_back_and_nest(self) -> None:
        """transaction() commits, rolls back, and nests with savepoints."""
        session = self.session()
        try:
            session.create_table(_ORDERS)
            with session.transaction():
                session.insert("order", {"id": 1, "customer": "kept", "code": "1"})
            try:
                with session.transaction():
                    session.insert("order", {"id": 2, "customer": "gone", "code": "2"})
                    raise _RollbackSignal
            except _RollbackSignal:
                pass
            with session.transaction():
                session.insert("order", {"id": 3, "customer": "outer", "code": "3"})
                try:
                    with session.transaction():
                        session.insert("order", {"id": 4, "customer": "inner", "code": "4"})
                        raise _RollbackSignal
                except _RollbackSignal:
                    pass
            ids = [row["id"] for row in session.select("order", columns=["id"], order_by=["id"])]
            assert ids == [1, 3]  # noqa: S101
            assert not session.in_transaction  # noqa: S101
        finally:
            session.close()

    def test_driver_errors_are_translated(self) -> None:
        """Integrity and programming errors become SqlError subclasses."""
        session = self.session()
        try:
            session.create_table(_ORDERS)
            session.insert("order", {"id": 1, "customer": "a", "code": "same"})
            try:
                session.insert("order", {"id": 2, "customer": "b", "code": "same"})
            except SqlIntegrityError:
                pass
            else:  # pragma: no cover - contract violation
                msg = "duplicate unique value was accepted"
                raise AssertionError(msg)
            try:
                session.execute("SELECT * FROM missing_table")
            except SqlProgrammingError:
                pass
            except Exception as exc:  # pragma: no cover - contract violation
                msg = f"expected SqlProgrammingError, got {type(exc).__name__}"
                raise AssertionError(msg) from exc
            else:  # pragma: no cover - contract violation
                msg = "querying a missing table did not fail"
                raise AssertionError(msg)
        finally:
            session.close()

    def test_capability_conformance(self) -> None:
        """The Capability built on this Provider honors the Core contract."""
        check_capability_conformance(
            SqlCapability(self.make_provider()),
            use=lambda session: session.scalar("SELECT 1"),
            concurrent_runs=4,
        )

    def test_open_transaction_is_rolled_back_at_finalize(self) -> None:
        """A transaction left open by the automation never leaks into the next one."""
        provider = self.make_provider()
        runtime = (
            RuntimeBuilder()
            .with_environment({}, prefix=None)
            .with_capability(SqlCapability(provider))
            .build()
        )

        def setup(ctx: ExecutionContext) -> None:
            ctx.capability(SqlCapability).create_table(_ORDERS)

        def leave_open(ctx: ExecutionContext) -> None:
            session = ctx.capability(SqlCapability)
            transaction = session.transaction()
            ctx.state["transaction"] = transaction  # keep it open (never exited)
            transaction.__enter__()
            session.insert("order", {"id": 1, "customer": "uncommitted", "code": "u"})

        def count(ctx: ExecutionContext) -> object:
            return ctx.capability(SqlCapability).scalar('SELECT count(*) FROM "order"')

        assert runtime.run(setup).succeeded  # noqa: S101
        assert runtime.run(leave_open).succeeded  # noqa: S101
        result = runtime.run(count)
        assert result.output == 0, result  # noqa: S101


class _RollbackSignal(Exception):  # noqa: N818 - control-flow signal of the tests
    pass
