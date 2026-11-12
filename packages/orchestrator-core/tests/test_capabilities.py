from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, ClassVar, Self

import pytest

from orchestrator_core import (
    Capability,
    CapabilityError,
    CapabilityNotFoundError,
    CapabilityUnavailableError,
    ConfigSection,
    ConfigurationError,
    DuplicateCapabilityError,
    ExecutionContext,
    ExecutionStatus,
    FunctionStage,
    IncompatibleCapabilityError,
    Phase,
    RuntimeBuilder,
    StageStatus,
)
from orchestrator_core._capabilities import is_api_compatible
from orchestrator_core.testing import check_capability_conformance


@dataclass
class Connection:
    label: str
    closed: bool = False

    def close(self) -> None:
        self.closed = True


@dataclass
class Counter:
    opened: int = 0
    closed: int = 0
    lock: threading.Lock = field(default_factory=threading.Lock)


class Database(Capability[Connection]):
    default_name = "db"
    core_api = "0.1"

    def __init__(self, label: str = "main", counter: Counter | None = None) -> None:
        self.label = label
        self.counter = counter or Counter()

    @classmethod
    def from_config(cls, section: ConfigSection, /, **options: Any) -> Self:
        section.check_keys({"label"})
        return cls(label=section.get_str("label", "main"), **options)

    def open(self, ctx: ExecutionContext) -> Connection:
        connection = Connection(f"{self.label}:{ctx.execution_id}")
        with self.counter.lock:
            self.counter.opened += 1
        ctx.resources.callback(self._close, connection)
        return connection

    def _close(self, connection: Connection) -> None:
        connection.close()
        with self.counter.lock:
            self.counter.closed += 1


class Cache(Capability[dict[str, str]]):
    default_name = "cache"

    def open(self, ctx: ExecutionContext) -> dict[str, str]:
        db = ctx.capability(Database)  # capabilities may use those registered before them
        return {"backed_by": db.label}


def test_registration_by_instance_and_by_class(builder: RuntimeBuilder) -> None:
    counter = Counter()
    runtime = (
        builder.with_settings({"capabilities": {"reports": {"label": "from-config"}}})
        .with_capability(Database("primary", counter))
        .with_capability(Database, name="reports", counter=counter)
        .build()
    )
    assert runtime.capabilities == ("db", "reports")

    def automation(ctx: ExecutionContext) -> tuple[str, str]:
        return ctx.capability(Database, "db").label, ctx.capability(Database, "reports").label

    result = runtime.run(automation)
    assert result.output == (
        f"primary:{result.execution_id}",
        f"from-config:{result.execution_id}",
    )
    assert counter.opened == counter.closed == 2


def test_lookup_errors(builder: RuntimeBuilder) -> None:
    runtime = builder.with_capability(Database()).with_capability(Database(), name="other").build()

    def ambiguous(ctx: ExecutionContext) -> None:
        ctx.capability(Database)

    result = runtime.run(ambiguous)
    assert isinstance(result.error, CapabilityError)
    assert "pass name=" in str(result.error)

    missing = runtime.run(lambda ctx: ctx.capability(Cache))
    assert isinstance(missing.error, CapabilityNotFoundError)

    wrong_type = runtime.run(lambda ctx: ctx.capability(Cache, "db"))
    assert isinstance(wrong_type.error, CapabilityNotFoundError)


def test_handles_are_not_available_before_provisioning(builder: RuntimeBuilder) -> None:
    early = FunctionStage("too_early", Phase.PREPARE, lambda ctx: ctx.capability(Database))
    runtime = builder.with_capability(Database()).with_stage(early, after="initialize").build()
    result = runtime.run(lambda ctx: None)
    assert result.stage("too_early").status is StageStatus.FAILED
    assert "has not been provisioned yet" in str(result.error)


def test_capabilities_are_provisioned_in_registration_order(
    builder: RuntimeBuilder,
) -> None:
    runtime = builder.with_capability(Database("primary")).with_capability(Cache()).build()
    result = runtime.run(lambda ctx: ctx.capability(Cache))
    assert result.output == {"backed_by": f"primary:{result.execution_id}"}

    reversed_order = (
        RuntimeBuilder()
        .with_environment({}, prefix=None)
        .with_capability(Cache())
        .with_capability(Database())
        .build()
    )
    result = reversed_order.run(lambda ctx: None)
    assert result.stage("provision_dependencies").status is StageStatus.FAILED


def test_provisioning_failure_releases_what_was_acquired(
    builder: RuntimeBuilder,
) -> None:
    counter = Counter()

    class Unavailable(Capability[None]):
        default_name = "unavailable"

        def verify(self) -> None:
            raise CapabilityUnavailableError("driver 'acme' is not installed")

        def open(self, ctx: ExecutionContext) -> None:  # pragma: no cover - never reached
            raise AssertionError

    runtime = (
        builder.with_capability(Database(counter=counter)).with_capability(Unavailable()).build()
    )
    result = runtime.run(lambda ctx: None)
    assert result.status is ExecutionStatus.FAILED
    assert isinstance(result.error, CapabilityUnavailableError)
    assert "while provisioning capability 'unavailable'" in result.error.__notes__
    assert result.stage("execute_automation").status is StageStatus.SKIPPED
    assert counter.opened == counter.closed == 1


def test_registration_errors(builder: RuntimeBuilder) -> None:
    with pytest.raises(DuplicateCapabilityError):
        RuntimeBuilder().with_environment({}, prefix=None).with_capability(
            Database()
        ).with_capability(Database()).build()
    with pytest.raises(CapabilityError, match="invalid capability name"):
        RuntimeBuilder().with_environment({}, prefix=None).with_capability(
            Database(), name="Bad-Name"
        ).build()
    with pytest.raises(CapabilityError, match="only be given together with a Capability class"):
        builder.with_capability(Database(), label="x")
    with pytest.raises(CapabilityError, match="is not a Capability"):
        RuntimeBuilder().with_environment({}, prefix=None).with_capability(
            object(),  # type: ignore[arg-type]
            name="thing",
        ).build()
    with pytest.raises(ConfigurationError, match=r"capabilities\.db: unknown key\(s\): lable"):
        RuntimeBuilder().with_environment({}, prefix=None).with_settings(
            {"capabilities": {"db": {"lable": "typo"}}}
        ).with_capability(Database).build()


def test_default_from_config_rejects_settings() -> None:
    with pytest.raises(ConfigurationError, match=r"capabilities\.cache: unknown key"):
        RuntimeBuilder().with_environment({}, prefix=None).with_settings(
            {"capabilities": {"cache": {"size": 1}}}
        ).with_capability(Cache).build()
    runtime = RuntimeBuilder().with_environment({}, prefix=None).with_capability(Cache).build()
    assert runtime.capabilities == ("cache",)


def test_incompatible_core_api_is_rejected() -> None:
    class FromTheFuture(Database):
        core_api: ClassVar[str | None] = "0.2"

    class Malformed(Database):
        core_api: ClassVar[str | None] = "one"

    for kind in (FromTheFuture, Malformed):
        with pytest.raises(IncompatibleCapabilityError, match="requires Core API"):
            RuntimeBuilder().with_environment({}, prefix=None).with_capability(kind()).build()


@pytest.mark.parametrize(
    ("required", "current", "expected"),
    [
        ("0.1", "0.1", True),
        ("0.1", "0.2", False),
        ("0.2", "0.1", False),
        ("1.0", "1.3", True),
        ("1.4", "1.3", False),
        ("1.0", "2.0", False),
        ("0.9", "1.0", False),
    ],
)
def test_api_compatibility_rules(required: str, current: str, expected: bool) -> None:
    assert is_api_compatible(required, current) is expected


def test_api_versions_must_be_major_minor() -> None:
    with pytest.raises(ValueError, match=r"major\.minor"):
        is_api_compatible("1", "1.0")


def test_conformance_helper_accepts_a_correct_capability() -> None:
    counter = Counter()
    check_capability_conformance(Database(counter=counter), use=lambda handle: handle.label)
    assert counter.opened == counter.closed == 11


def test_conformance_helper_rejects_shared_handles_and_failures() -> None:
    shared = Connection("shared")

    class Leaky(Capability[Connection]):
        default_name = "leaky"

        def open(self, ctx: ExecutionContext) -> Connection:
            return shared

    with pytest.raises(AssertionError, match="more than one execution"):
        check_capability_conformance(Leaky())

    class Broken(Capability[None]):
        default_name = "broken"

        def open(self, ctx: ExecutionContext) -> None:
            raise RuntimeError("cannot connect")

    with pytest.raises(AssertionError, match=r"execution\(s\) failed"):
        check_capability_conformance(Broken(), concurrent_runs=2)
