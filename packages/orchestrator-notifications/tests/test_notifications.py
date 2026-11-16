from __future__ import annotations

import logging
from collections.abc import Callable

import pytest

from orchestrator_core import (
    CancellationToken,
    CapabilityError,
    ConfigSection,
    ConfigurationError,
    ExecutionContext,
    ExecutionStatus,
    RuntimeBuilder,
    SecretStore,
)
from orchestrator_core.testing import EventRecorder, InMemoryMetrics, InMemoryRecordSink
from orchestrator_notifications import (
    NOTIFICATIONS_FAILED,
    ChannelSettings,
    DeliveryStatus,
    LifecycleNotice,
    Notification,
    NotificationCapability,
    NotificationChannel,
    NotificationError,
    NotificationFailed,
    Notifier,
    NotifyOutcome,
    NotifyStarted,
    Severity,
    default_formatter,
)
from orchestrator_notifications._notifier import notify_lifecycle
from orchestrator_notifications.testing import InMemoryChannel, NotificationChannelContract

SENTINEL = "S3NT1NEL-notifications-91c2"


class _Sentinel:
    def resolve(self, target: str) -> str:
        return f"{SENTINEL}-{target}"


def _builder(capability: NotificationCapability) -> RuntimeBuilder:
    return (
        RuntimeBuilder()
        .with_environment({}, prefix=None)
        .with_secret_resolver("test", _Sentinel())
        .with_capability(capability)
    )


def test_notification_validation_and_facts() -> None:
    note = Notification(subject="Lote", body="ok", facts=[("a", "1")], severity="warning")  # type: ignore[arg-type]
    assert note.facts == (("a", "1"),)
    assert note.severity is Severity.WARNING
    with pytest.raises(ValueError, match="subject"):
        Notification(subject=" ", body="x")
    with pytest.raises(ValueError, match="kind"):
        Notification(subject="s", body="x", kind="Bad Kind")
    with pytest.raises(TypeError, match="pairs"):
        Notification(subject="s", body="x", facts=["a"])  # type: ignore[list-item]


def test_send_to_named_and_default_channels() -> None:
    ops, team = InMemoryChannel(), InMemoryChannel()
    capability = NotificationCapability(
        {"ops": ops, "team": team}, default_channels=["ops", "team"]
    )

    def automation(ctx: ExecutionContext) -> int:
        notifier = ctx.capability(NotificationCapability)
        first = notifier.send(Notification(subject="a", body="1"))
        second = notifier.send(Notification(subject="b", body="2"), channel="team")
        assert [r.status for r in (*first, *second)] == [DeliveryStatus.SENT] * 3
        assert notifier.channels == ("ops", "team")
        return len(notifier.reports)

    result = _builder(capability).build().run(automation)
    assert result.succeeded, result.error
    assert result.output == 3
    assert [n.subject for n in ops.sent] == ["a"]
    assert [n.subject for n in team.sent] == ["a", "b"]


def test_unknown_or_missing_channel_is_a_programming_error() -> None:
    capability = NotificationCapability({"ops": InMemoryChannel()})

    def automation(ctx: ExecutionContext) -> None:
        notifier = ctx.capability(NotificationCapability)
        with pytest.raises(CapabilityError, match="no channel"):
            notifier.send(Notification(subject="a", body="1"))
        with pytest.raises(CapabilityError, match="unknown notification channel"):
            notifier.send(Notification(subject="a", body="1"), channel="nope")

    assert _builder(capability).build().run(automation).succeeded


def test_texts_are_masked_before_leaving_the_process() -> None:
    channel = InMemoryChannel()
    capability = NotificationCapability({"ops": channel}, default_channels=["ops"])

    def automation(ctx: ExecutionContext) -> None:
        token = ctx.secrets.resolve("test:api").reveal()
        ctx.capability(NotificationCapability).send(
            Notification(subject=f"key {token}", body=f"body {token}", facts=(("k", token),))
        )

    assert _builder(capability).build().run(automation).succeeded
    (sent,) = channel.sent
    text = f"{sent.subject} {sent.body} {sent.facts}"
    assert SENTINEL not in text
    assert "***" in sent.subject


def test_a_failing_channel_is_reported_without_changing_the_outcome(
    caplog: pytest.LogCaptureFixture,
) -> None:
    events, metrics = EventRecorder(), InMemoryMetrics()
    capability = NotificationCapability({"ops": InMemoryChannel(fail=1)}, default_channels=["ops"])
    runtime = (
        _builder(capability).with_metrics(metrics).on_event(NotificationFailed, events).build()
    )

    def automation(ctx: ExecutionContext) -> str:
        (report,) = ctx.capability(NotificationCapability).send(
            Notification(subject="s", body="b", kind="batch.done")
        )
        return report.status.value

    with caplog.at_level(logging.WARNING):
        result = runtime.run(automation)
    assert result.succeeded
    assert result.output == "failed"
    (event,) = events.of_type(NotificationFailed)
    assert (event.channel, event.kind) == ("ops", "batch.done")
    assert "refused" in event.error.message
    assert metrics.counter(NOTIFICATIONS_FAILED, channel="ops", kind="batch.done") == 1
    assert "notification 'batch.done' to channel 'ops' failed" in caplog.text


@pytest.mark.parametrize(
    ("channel_required", "call_required", "raises"),
    [(True, None, True), (False, True, True), (True, False, False), (False, None, False)],
)
def test_required_policy_per_channel_and_per_notification(
    channel_required: bool, call_required: bool | None, raises: bool
) -> None:
    capability = NotificationCapability(
        {"ops": ChannelSettings(InMemoryChannel(fail=1), required=channel_required)},
        default_channels=["ops"],
    )

    def automation(ctx: ExecutionContext) -> None:
        ctx.capability(NotificationCapability).send(
            Notification(subject="s", body="b"), required=call_required
        )

    result = _builder(capability).build().run(automation)
    assert result.succeeded is not raises
    if raises:
        assert isinstance(result.error, NotificationError)
        assert "required notification channel 'ops' failed" in str(result.error)


def test_retry_only_for_retryable_errors() -> None:
    retryable = InMemoryChannel(fail=2, retryable=True)
    final = InMemoryChannel(fail=1, retryable=False)
    capability = NotificationCapability(
        {
            "flaky": ChannelSettings(retryable, attempts=3, delay=0.0),
            "final": ChannelSettings(final, attempts=3),
        }
    )

    def automation(ctx: ExecutionContext) -> list[tuple[str, int]]:
        notifier = ctx.capability(NotificationCapability)
        reports = [
            *notifier.send(Notification(subject="s", body="b"), channel="flaky"),
            *notifier.send(Notification(subject="s", body="b"), channel="final"),
        ]
        return [(r.status.value, r.attempts) for r in reports]

    result = _builder(capability).build().run(automation)
    assert result.output == [("sent", 3), ("failed", 1)]


def _automation_for(status: str) -> tuple[Callable[[ExecutionContext], None], dict[str, object]]:
    if status == "succeeded":
        return (lambda ctx: None), {}
    if status == "failed":

        def fail(ctx: ExecutionContext) -> None:
            msg = "batch rejected"
            raise ValueError(msg)

        return fail, {}
    if status == "cancelled":
        token = CancellationToken()

        def cancel(ctx: ExecutionContext) -> None:
            token.cancel()
            ctx.check()

        return cancel, {"cancellation": token}

    def slow(ctx: ExecutionContext) -> None:
        ctx.sleep(5)

    return slow, {"timeout": 0.05}


@pytest.mark.parametrize("status", ["succeeded", "failed", "cancelled", "timed_out"])
@pytest.mark.parametrize("required", [False, True])
@pytest.mark.parametrize("available", [True, False])
def test_outcome_notice_matrix(status: str, required: bool, available: bool) -> None:
    channel = InMemoryChannel(fail=0 if available else 1)
    capability = NotificationCapability(
        {"ops": ChannelSettings(channel, required=required)},
        lifecycle={status: ["ops"]},
    )
    runtime = _builder(capability).with_stage(NotifyOutcome(), after="finalize").build()
    automation, options = _automation_for(status)
    result = runtime.run(automation, **options)  # type: ignore[arg-type]
    expected = "failed" if (required and not available and status == "succeeded") else status
    assert result.status.value == expected
    stage = result.stage("notify_outcome")
    assert (stage.error is None) is (available or not required)
    if available:
        (sent,) = channel.sent
        assert sent.kind == f"execution.{status}"
        assert "Informamos que a execução" in sent.body
    else:
        assert channel.sent == ()


@pytest.mark.parametrize(("required", "available"), [(False, False), (True, False), (True, True)])
def test_started_notice_runs_before_the_automation(required: bool, available: bool) -> None:
    channel = InMemoryChannel(fail=0 if available else 1)
    capability = NotificationCapability(
        {"ops": ChannelSettings(channel, required=required)}, lifecycle={"started": ["ops"]}
    )
    calls: list[str] = []
    runtime = _builder(capability).with_stage(NotifyStarted(), after="prepare_execution").build()
    result = runtime.run(lambda ctx: calls.append("ran"))
    blocked = required and not available
    assert result.succeeded is not blocked
    assert calls == ([] if blocked else ["ran"])
    if available:
        assert channel.sent[0].kind == "execution.started"


def test_lifecycle_without_its_stages_is_refused_before_the_automation() -> None:
    capability = NotificationCapability(
        {"ops": InMemoryChannel()}, lifecycle={"started": ["ops"], "failed": ["ops"]}
    )
    calls: list[str] = []
    result = _builder(capability).build().run(lambda ctx: calls.append("ran"))
    assert result.status is ExecutionStatus.FAILED
    assert isinstance(result.error, ConfigurationError)
    assert "notify_started, notify_outcome" in str(result.error)
    assert calls == []


def test_started_stage_before_provisioning_is_refused() -> None:
    capability = NotificationCapability({"ops": InMemoryChannel()}, lifecycle={"started": ["ops"]})
    runtime = _builder(capability).with_stage(NotifyStarted(), after="initialize").build()
    result = runtime.run(lambda ctx: None)
    assert result.status is ExecutionStatus.FAILED


def test_outcome_stage_without_the_capability_is_a_configuration_error() -> None:
    runtime = (
        RuntimeBuilder()
        .with_environment({}, prefix=None)
        .with_stage(NotifyOutcome(), after="finalize")
        .build()
    )
    result = runtime.run(lambda ctx: None)
    assert result.status is ExecutionStatus.FAILED
    assert result.stage("notify_outcome").error is not None


def test_outcome_notice_is_skipped_with_a_warning_when_the_capability_was_not_opened(
    caplog: pytest.LogCaptureFixture,
) -> None:
    from orchestrator_core import Capability

    class Broken(Capability[None]):
        default_name = "broken"

        def open(self, ctx: ExecutionContext) -> None:
            msg = "database unavailable"
            raise RuntimeError(msg)

    channel = InMemoryChannel()
    capability = NotificationCapability({"ops": channel}, lifecycle={"failed": ["ops"]})
    runtime = (
        RuntimeBuilder()
        .with_environment({}, prefix=None)
        .with_capability(Broken())  # opened first and fails: notifications never opens
        .with_capability(capability)
        .with_stage(NotifyOutcome(), after="finalize")
        .build()
    )
    with caplog.at_level(logging.WARNING):
        result = runtime.run(lambda ctx: None)
    assert result.status is ExecutionStatus.FAILED
    assert result.stage("notify_outcome").error is None
    assert channel.sent == ()
    assert "no failed notice was sent" in caplog.text


def test_notifications_opened_first_report_the_failure_of_later_capabilities() -> None:
    from orchestrator_core import Capability

    class Broken(Capability[None]):
        default_name = "broken"

        def open(self, ctx: ExecutionContext) -> None:
            msg = "database unavailable"
            raise RuntimeError(msg)

    channel = InMemoryChannel()
    runtime = (
        RuntimeBuilder()
        .with_environment({}, prefix=None)
        .with_capability(NotificationCapability({"ops": channel}, lifecycle={"failed": ["ops"]}))
        .with_capability(Broken())
        .with_stage(NotifyOutcome(), after="finalize")
        .build()
    )
    result = runtime.run(lambda ctx: None)
    assert result.status is ExecutionStatus.FAILED
    (sent,) = channel.sent
    assert "RuntimeError: database unavailable" in dict(sent.facts)["Erro"]


def test_lifecycle_notice_is_sent_at_most_once_per_status_and_channel() -> None:
    channel = InMemoryChannel()
    capability = NotificationCapability({"ops": channel}, lifecycle={"succeeded": ["ops"]})
    runtime = _builder(capability).with_stage(NotifyOutcome(), after="finalize").build()

    def automation(ctx: ExecutionContext) -> list[str]:
        notifier = ctx.capability(NotificationCapability)
        notice = LifecycleNotice(
            status="succeeded",
            automation=ctx.automation,
            runtime=ctx.runtime,
            execution_id=ctx.execution_id,
            started_at=ctx.started_at,
        )
        first = notify_lifecycle(notifier, notice)
        second = notify_lifecycle(notifier, notice)
        return [r.status.value for r in (*first, *second)]

    result = runtime.run(automation)
    assert result.output == ["sent", "skipped"]
    assert len(channel.sent) == 1  # the outcome stage found it already sent
    assert result.stage("notify_outcome").error is None


def test_sentinel_never_reaches_notices_reports_logs_events_or_records() -> None:
    import io

    from orchestrator_core.logs import configure_logging

    events, sink = EventRecorder(), InMemoryRecordSink()
    channel = InMemoryChannel()
    failing = InMemoryChannel(fail=5)
    capability = NotificationCapability(
        {"ops": channel, "bad": failing}, lifecycle={"failed": ["ops", "bad"]}
    )
    runtime = (
        _builder(capability)
        .with_stage(NotifyOutcome(), after="finalize")
        .on_event(NotificationFailed, events)
        .with_record_sink(sink)
        .build()
    )

    def automation(ctx: ExecutionContext) -> None:
        secret = ctx.secrets.resolve("test:db").reveal()
        msg = f"login failed for {secret}"
        raise RuntimeError(msg)

    stream = io.StringIO()
    handler = configure_logging("DEBUG", stream=stream, logger="orchestrator")
    try:
        result = runtime.run(automation)
    finally:
        logging.getLogger("orchestrator").removeHandler(handler)
    assert result.status is ExecutionStatus.FAILED
    (sent,) = channel.sent
    assert "channel 'bad' failed" in stream.getvalue()
    texts = [
        sent.subject,
        sent.body,
        str(sent.facts),
        stream.getvalue(),
        str(events.events),
        str([record.to_dict() for record in sink.records]),
    ]
    assert all(SENTINEL not in text for text in texts)
    assert "login failed for ***" in dict(sent.facts)["Erro"]


def test_from_config_builds_channels_policies_and_lifecycle() -> None:
    settings = {
        "capabilities": {
            "notifications": {
                "default_channels": ["ops"],
                "lifecycle": {"failed": ["ops", "team"], "succeeded": []},
                "channels": {
                    "ops": {"provider": "memory", "required": True, "attempts": 2, "delay": 0.0},
                    "team": {"provider": "memory", "fail": 1},
                },
            }
        }
    }
    runtime = (
        RuntimeBuilder()
        .with_environment({}, prefix=None)
        .with_settings(settings)
        .with_capability(NotificationCapability, providers={"memory": InMemoryChannel})
        .with_stage(NotifyOutcome(), after="finalize")
        .build()
    )
    result = runtime.run(lambda ctx: ctx.capability(NotificationCapability).channels)
    assert result.output == ("ops", "team")


@pytest.mark.parametrize(
    ("table", "message"),
    [
        ({"channels": {"ops": {"provider": "nope"}}}, "provider"),
        ({"channels": {"ops": {"provider": "memory", "typo": 1}}}, "unknown key"),
        ({"default_channels": ["missing"]}, "unknown channel 'missing'"),
        ({"lifecycle": {"finished": []}}, "unknown key"),
        ({"default_channels": "ops"}, "expected a list"),
        ({"extra": True}, "unknown key"),
        ({"channels": {"ops": {"provider": "memory", "attempts": 0}}}, "attempts"),
    ],
)
def test_invalid_configuration_is_refused(table: dict[str, object], message: str) -> None:
    with pytest.raises(ConfigurationError, match=message):
        NotificationCapability.from_config(
            ConfigSection(table, "capabilities.notifications"),
            providers={"memory": InMemoryChannel},
        )


def test_from_config_requires_the_providers_mapping() -> None:
    with pytest.raises(CapabilityError, match="providers"):
        NotificationCapability.from_config(ConfigSection({}, "capabilities.notifications"))


def test_default_formatter_is_formal_portuguese() -> None:
    from datetime import UTC, datetime

    from orchestrator_core import ErrorInfo

    notice = LifecycleNotice(
        status="failed",
        automation="faturamento",
        runtime="producao",
        execution_id="e1",
        started_at=datetime(2026, 11, 15, 12, 0, tzinfo=UTC),
        duration=12.34,
        error=ErrorInfo(type="ValueError", message="lote inválido"),
    )
    note = default_formatter(notice)
    assert note.subject == "[faturamento] Execução concluída com falha"
    assert note.severity is Severity.ERROR
    assert note.kind == "execution.failed"
    assert note.dedup_key == "e1:execution.failed"
    facts = dict(note.facts)
    assert facts["Duração"] == "12.3 s"
    assert facts["Início"] == "2026-11-15 12:00:00 UTC"
    assert facts["Erro"] == "ValueError: lote inválido"
    assert note.body.startswith("Informamos que a execução da automação faturamento")


def test_custom_formatter_replaces_the_texts() -> None:
    channel = InMemoryChannel()

    def english(notice: LifecycleNotice) -> Notification:
        return Notification(subject=f"{notice.automation}: {notice.status}", body="done")

    capability = NotificationCapability(
        {"ops": channel}, lifecycle={"succeeded": ["ops"]}, formatter=english
    )
    runtime = _builder(capability).with_stage(NotifyOutcome(), after="finalize").build()
    assert runtime.run(lambda ctx: None, name="billing").succeeded
    assert channel.sent[0].subject == "billing: succeeded"


def test_channel_settings_validation() -> None:
    with pytest.raises(ValueError, match="attempts"):
        ChannelSettings(InMemoryChannel(), attempts=0)
    with pytest.raises(ValueError, match="delay"):
        ChannelSettings(InMemoryChannel(), delay=-1)
    with pytest.raises(ValueError, match="invalid channel name"):
        NotificationCapability({"Bad Name": InMemoryChannel()})
    with pytest.raises(ValueError, match="unknown lifecycle status"):
        NotificationCapability({"ops": InMemoryChannel()}, lifecycle={"done": ["ops"]})


def test_verify_reaches_every_channel() -> None:
    verified: list[str] = []

    class Checked(InMemoryChannel):
        def verify(self) -> None:
            verified.append("yes")

    NotificationCapability({"a": Checked(), "b": Checked()}).verify()
    assert verified == ["yes", "yes"]


class _Unprintable(Exception):
    def __str__(self) -> str:
        msg = "broken"
        raise RuntimeError(msg)


def test_a_provider_bug_is_a_failed_delivery() -> None:
    class Buggy(NotificationChannel):
        @classmethod
        def from_config(cls, section: ConfigSection) -> Buggy:
            return cls()

        def send(self, notification: Notification, secrets: SecretStore) -> None:
            raise _Unprintable

        def describe(self) -> str:
            return "buggy"

    capability = NotificationCapability({"ops": Buggy()}, default_channels=["ops"])

    def automation(ctx: ExecutionContext) -> str | None:
        (report,) = ctx.capability(NotificationCapability).send(Notification(subject="s", body="b"))
        return None if report.error is None else report.error.message

    result = _builder(capability).build().run(automation)
    assert result.succeeded
    assert result.output == "<exception str() failed>"


def test_the_notifier_is_the_handle_of_each_execution() -> None:
    capability = NotificationCapability({"ops": InMemoryChannel()})
    result = _builder(capability).build().run(lambda ctx: ctx.capability(NotificationCapability))
    assert isinstance(result.output, Notifier)


class TestInMemoryChannelContract(NotificationChannelContract):
    def setup_method(self) -> None:
        self.channel = InMemoryChannel()

    def make_channel(self) -> NotificationChannel:
        return self.channel

    def received(self) -> list[str]:
        return [f"{n.subject}\n{n.body}\n{n.facts}" for n in self.channel.sent]

    def make_failing_channel(self) -> NotificationChannel:
        return InMemoryChannel(fail=1)
