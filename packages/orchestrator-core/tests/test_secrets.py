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
