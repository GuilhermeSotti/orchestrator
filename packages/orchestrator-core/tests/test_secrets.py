from __future__ import annotations

import io
import json
import logging
import pickle
from pathlib import Path

import pytest

from orchestrator_core import (
    Event,
    ExecutionContext,
    ExecutionOutcome,
    FunctionStage,
    Phase,
    RuntimeBuilder,
    Secret,
    SecretRef,
    SecretResolutionError,
    SecretStore,
)
from orchestrator_core._redaction import Redactor
from orchestrator_core._secrets import EnvSecretResolver, FileSecretResolver
from orchestrator_core.logs import configure_logging
from orchestrator_core.testing import EventRecorder, InMemoryRecordSink

SENTINEL = "S3NT1NEL-do-not-leak-7f3a"


def test_secret_never_reveals_itself() -> None:
    secret = Secret(SENTINEL)
    assert secret.reveal() == SENTINEL
    for text in (
        repr(secret),
        str(secret),
        f"{secret}",
        f"{secret:>40}",
        "%s" % (secret,),  # noqa: UP031 - %-formatting must be masked too
    ):
        assert SENTINEL not in text
    assert secret == Secret(SENTINEL)
    assert secret != Secret("other-value")
    assert secret.__eq__("plain") is NotImplemented
    with pytest.raises(TypeError):
        hash(secret)
    with pytest.raises(TypeError, match="cannot be pickled"):
        pickle.dumps(secret)


def test_secret_reference_parsing() -> None:
    assert SecretRef.parse(" env:DB_PASSWORD ") == SecretRef("env", "DB_PASSWORD")
    assert str(SecretRef.parse("file:/run/secrets/db")) == "file:/run/secrets/db"
    for text in ("no-scheme", "UPPER:x", ":empty", "env:"):
        with pytest.raises(ValueError) as info:
            SecretRef.parse(text)
        assert text.strip(":") not in str(info.value) or text == "env:"


def test_builtin_resolvers(tmp_path: Path) -> None:
    assert EnvSecretResolver({"TOKEN": "abc-123"}).resolve("TOKEN") == "abc-123"
    with pytest.raises(SecretResolutionError, match="'MISSING' is not set"):
        EnvSecretResolver({}).resolve("MISSING")
    secret_file = tmp_path / "db"
    secret_file.write_text("from-file\n", encoding="utf-8")
    assert FileSecretResolver().resolve(str(secret_file)) == "from-file"
    with pytest.raises(SecretResolutionError, match="cannot read secret file"):
        FileSecretResolver().resolve(str(tmp_path / "absent"))


class _Exploding:
    def resolve(self, target: str) -> str:
        raise RuntimeError(f"backend failed while fetching {SENTINEL}")


class _NotAString:
    def resolve(self, target: str) -> str:
        return 42  # type: ignore[return-value]


def test_secret_store_errors_never_leak_values() -> None:
    redactor = Redactor()
    store = SecretStore(
        {
            "env": EnvSecretResolver({"A": SENTINEL}),
            "boom": _Exploding(),
            "num": _NotAString(),
        },
        redactor,
    )
    assert store.schemes == ("boom", "env", "num")
    assert store.resolve("env:A").reveal() == SENTINEL
    assert redactor.redact(f"x{SENTINEL}y") == "x***y"
    with pytest.raises(
        SecretResolutionError, match="no secret resolver registered for scheme 'vault'"
    ):
        store.resolve("vault:path")
    with pytest.raises(SecretResolutionError) as info:
        store.resolve("boom:x")
    assert SENTINEL not in str(info.value)
    assert info.value.__cause__ is None
    with pytest.raises(SecretResolutionError, match="non-string"):
        store.resolve("num:x")
    with pytest.raises(SecretResolutionError, match="expected a secret reference"):
        store.resolve("literal-value")


def test_redactor_rules() -> None:
    redactor = Redactor()
    redactor.register("abc")
    assert len(redactor) == 0
    redactor.register("secret")
    redactor.register("secret-longer")
    assert redactor.redact("a secret-longer b secret") == "a *** b ***"
    assert redactor.redact("") == ""
    redactor.clear()
    assert redactor.redact("secret") == "secret"


def test_sentinel_secret_never_reaches_logs_events_records_or_repr() -> None:
    """MVP criterion 6: no secret value appears in logs, events or records."""
    stream = io.StringIO()
    json_stream = io.StringIO()
    handler = configure_logging("DEBUG", stream=stream, logger="orchestrator")
    json_handler = configure_logging(
        "DEBUG", stream=json_stream, logger="orchestrator_core", json_output=True
    )
    recorder = EventRecorder()
    sink = InMemoryRecordSink()
    runtime = (
        RuntimeBuilder()
        .with_environment({}, prefix=None)
        .with_secret_resolver("env", EnvSecretResolver({"API_TOKEN": SENTINEL}))
        .on_event(Event, recorder)
        .with_record_sink(sink)
        .build()
    )

    def leaky(ctx: ExecutionContext) -> None:
        token = ctx.secrets.resolve("env:API_TOKEN")
        ctx.logger.info("calling the API with token=%s", token.reveal())
        logging.getLogger("orchestrator_core.leak").error("plain log with %s", token.reveal())
        raise RuntimeError(f"request failed with token {token.reveal()}")

    try:
        result = runtime.run(leaky)
    finally:
        logging.getLogger("orchestrator").removeHandler(handler)
        logging.getLogger("orchestrator_core").removeHandler(json_handler)

    assert result.status.value == "failed"
    texts = [
        stream.getvalue(),
        json_stream.getvalue(),
        repr(result),
        json.dumps(result.record.to_dict()),
        json.dumps([r.to_dict() for r in sink.records]),
        repr(recorder.events),
    ]
    for text in texts:
        assert SENTINEL not in text
    assert "token=***" in stream.getvalue()
    assert "request failed with token ***" in json_stream.getvalue()
    assert result.record.error is not None
    assert result.record.error.message == "request failed with token ***"
    assert SENTINEL in str(result.error)  # the raw exception is kept for programmatic use


def test_redact_and_error_info_protect_text_built_by_finalizers_and_teardown_stages() -> None:
    """RFC-0005, 2.1 (E7.3): text sent out by teardown code can be masked by the public API."""
    sent: list[str] = []

    def report(ctx: ExecutionContext) -> None:
        outcome = ctx.outcome
        assert outcome is not None
        sent.append(ctx.redact(f"stage saw {outcome.error}"))

    runtime = (
        RuntimeBuilder()
        .with_environment({}, prefix=None)
        .with_secret_resolver("env", EnvSecretResolver({"API_TOKEN": SENTINEL}))
        .with_stage(FunctionStage("report", Phase.TEARDOWN, report), after="finalize")
        .build()
    )

    def automation(ctx: ExecutionContext) -> None:
        token = ctx.secrets.resolve("env:API_TOKEN").reveal()

        def notify(outcome: ExecutionOutcome) -> None:
            assert outcome.error_info is not None
            sent.append(f"{outcome.error_info.type}: {outcome.error_info.message}")
            sent.append(ctx.redact(f"raw: {outcome.error}"))
            sent.append(ctx.redact("text without secrets stays intact"))

        ctx.add_finalizer(notify)
        raise RuntimeError(f"request failed with token {token}")

    result = runtime.run(automation)
    assert result.status.value == "failed"
    assert SENTINEL in str(result.error)  # the raw exception still has it
    assert sent == [
        "RuntimeError: request failed with token ***",
        "raw: request failed with token ***",
        "text without secrets stays intact",
        "stage saw request failed with token ***",
    ]
    for text in sent:
        assert SENTINEL not in text


def test_make_secret_store_resolves_with_a_private_masking_registry() -> None:
    from orchestrator_core._redaction import default_redactor
    from orchestrator_core.testing import make_secret_store

    private = "only-in-the-test-store-4b1d"

    class Fixed:
        def resolve(self, target: str) -> str:
            return f"{private}-{target}"

    store = make_secret_store({"test": Fixed()})
    assert store.schemes == ("env", "file", "test")
    assert store.resolve("test:db").reveal() == f"{private}-db"
    assert default_redactor.redact(f"{private}-db") == f"{private}-db"  # not registered there
    with pytest.raises(SecretResolutionError, match="no secret resolver"):
        make_secret_store().resolve("kv:any")
    with pytest.raises(SecretResolutionError, match="is not set"):
        make_secret_store().resolve("env:ORCHESTRATOR_TEST_SURELY_UNSET_9d1e")


class _CountingResolver:
    """Resolver that counts calls and can fail on demand."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.fail = False

    def resolve(self, target: str) -> str:
        self.calls.append(target)
        if self.fail:
            msg = "backend unavailable"
            raise SecretResolutionError(msg)
        return f"value-of-{target}-{len(self.calls)}"


def test_each_reference_is_resolved_once_per_execution() -> None:
    resolver = _CountingResolver()
    runtime = (
        RuntimeBuilder()
        .with_environment({}, prefix=None)
        .with_secret_resolver("count", resolver)
        .build()
    )
    stores: list[SecretStore] = []

    def automation(ctx: ExecutionContext) -> tuple[str, str, str]:
        stores.append(ctx.secrets)
        first = ctx.secrets.resolve("count:db").reveal()
        again = ctx.secrets.resolve(SecretRef("count", "db")).reveal()
        other = ctx.secrets.resolve("count:api").reveal()
        return first, again, other

    first = runtime.run(automation)
    assert first.succeeded, first.error
    assert first.output == ("value-of-db-1", "value-of-db-1", "value-of-api-2")
    assert resolver.calls == ["db", "api"]
    second = runtime.run(automation)  # a new execution starts without the previous cache
    assert second.output == ("value-of-db-3", "value-of-db-3", "value-of-api-4")
    assert resolver.calls == ["db", "api", "db", "api"]
    # The shutdown stage discarded the values: the store resolves again, and keeps nothing.
    assert stores[0].resolve("count:db").reveal() == "value-of-db-5"
    assert stores[0].resolve("count:db").reveal() == "value-of-db-6"


def test_failed_resolutions_are_not_kept() -> None:
    from orchestrator_core.testing import make_secret_store

    resolver = _CountingResolver()
    store = make_secret_store({"count": resolver})
    resolver.fail = True
    for _ in range(2):
        with pytest.raises(SecretResolutionError, match="backend unavailable"):
            store.resolve("count:db")
    resolver.fail = False
    assert store.resolve("count:db").reveal() == "value-of-db-3"
    assert store.resolve("count:db").reveal() == "value-of-db-3"
    assert resolver.calls == ["db", "db", "db"]


def test_concurrent_resolutions_return_one_value() -> None:
    import threading
    from concurrent.futures import ThreadPoolExecutor

    from orchestrator_core.testing import make_secret_store

    barrier = threading.Barrier(8)

    class Slow:
        def __init__(self) -> None:
            self.count = 0
            self.lock = threading.Lock()

        def resolve(self, target: str) -> str:
            with self.lock:
                self.count += 1
                current = self.count
            barrier.wait(timeout=5)
            return f"{target}-{current}"

    store = make_secret_store({"slow": Slow()})
    with ThreadPoolExecutor(max_workers=8) as pool:
        values = list(pool.map(lambda _: store.resolve("slow:db").reveal(), range(8)))
    assert len(set(values)) == 1  # every caller gets the value kept first
