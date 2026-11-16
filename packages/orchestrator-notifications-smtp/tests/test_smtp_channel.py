from __future__ import annotations

import email
import logging
import smtplib
import ssl
from email import policy
from typing import Any, ClassVar

import pytest

from orchestrator_core import (
    ConfigSection,
    ConfigurationError,
    ExecutionStatus,
    RuntimeBuilder,
    SecretResolver,
)
from orchestrator_core.testing import make_secret_store
from orchestrator_notifications import (
    Notification,
    NotificationCapability,
    NotificationChannel,
    NotificationError,
    NotifyOutcome,
)
from orchestrator_notifications.testing import NotificationChannelContract
from orchestrator_notifications_smtp import SmtpChannel

SENTINEL = "S3NT1NEL-smtp-password-5e0a"
RECIPIENT = "operacao@exemplo.com"


class _Fixed:
    def resolve(self, target: str) -> str:
        return f"{SENTINEL}-{target}"


def _channel(server: Any, **overrides: Any) -> SmtpChannel:
    options: dict[str, Any] = {
        "host": "127.0.0.1",
        "port": server.port,
        "security": "none",
        "username": "automacao@exemplo.com",
        "password": "test:smtp",
        "sender": "automacao@exemplo.com",
        "to": [RECIPIENT],
        "timeout": 5.0,
    }
    options.update(overrides)
    return SmtpChannel(**options)


class TestSmtpContract(NotificationChannelContract):
    @pytest.fixture(autouse=True)
    def _server(self, smtp_server: Any) -> None:
        self.server = smtp_server

    def make_channel(self) -> NotificationChannel:
        return _channel(self.server)

    def received(self) -> list[str]:
        return list(self.server.messages)

    def make_failing_channel(self) -> NotificationChannel:
        self.server.refuse_recipients = True
        return _channel(self.server)

    def make_unresponsive_channel(self, timeout: float) -> NotificationChannel:
        self.server.silent = True
        return _channel(self.server, timeout=timeout)

    def secret_resolvers(self) -> dict[str, SecretResolver]:
        return {"test": _Fixed()}

    def private_values(self) -> list[str]:
        return [SENTINEL, RECIPIENT]


def test_message_headers_body_facts_and_message_id(smtp_server: Any) -> None:
    channel = _channel(smtp_server, cc=["equipe@exemplo.com"])
    note = Notification(
        subject="Execução concluída",
        body="Informamos que terminou.",
        facts=(("Lote", "42"),),
        dedup_key="e1:execution.succeeded",
    )
    channel.send(note, make_secret_store({"test": _Fixed()}))
    channel.send(note, make_secret_store({"test": _Fixed()}))
    first, second = (
        email.message_from_string(m, policy=policy.default) for m in smtp_server.messages
    )
    assert first["Subject"] == "Execução concluída"
    assert first["To"] == RECIPIENT
    assert first["Cc"] == "equipe@exemplo.com"
    assert first["Message-ID"] == second["Message-ID"]  # derived from the dedup key
    assert first["Message-ID"].endswith("@exemplo.com>")
    body = first.get_content()
    assert "Informamos que terminou." in body
    assert "Lote: 42" in body
    assert smtp_server.auth == [("PLAIN", f"\x00automacao@exemplo.com\x00{SENTINEL}-smtp")] * 2


def test_without_dedup_key_each_message_gets_its_own_id(smtp_server: Any) -> None:
    channel = _channel(smtp_server, username=None, password=None)
    for _ in range(2):
        channel.send(Notification(subject="s", body="b"), make_secret_store())
    ids = {email.message_from_string(m)["Message-ID"] for m in smtp_server.messages}
    assert len(ids) == 2
    assert smtp_server.auth == []


def test_xoauth2_token(smtp_server: Any) -> None:
    channel = _channel(smtp_server, password=None, token="test:oauth")
    channel.send(Notification(subject="s", body="b"), make_secret_store({"test": _Fixed()}))
    assert smtp_server.auth == [
        ("XOAUTH2", f"user=automacao@exemplo.com\x01auth=Bearer {SENTINEL}-oauth\x01\x01")
    ]


def test_authentication_failure_is_not_retryable_and_hides_the_password(
    smtp_server: Any,
) -> None:
    smtp_server.fail_auth = True
    with pytest.raises(NotificationError, match="authentication failed") as caught:
        _channel(smtp_server).send(
            Notification(subject="s", body="b"), make_secret_store({"test": _Fixed()})
        )
    assert caught.value.retryable is False
    assert SENTINEL not in str(caught.value)
    assert caught.value.__cause__ is None


def test_unreachable_server_is_retryable() -> None:
    import socket

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    channel = SmtpChannel(
        host="127.0.0.1",
        port=port,
        security="none",
        sender="a@exemplo.com",
        to=["b@exemplo.com"],
        timeout=2,
    )
    with pytest.raises(NotificationError, match="connect failed") as caught:
        channel.send(Notification(subject="s", body="b"), make_secret_store())
    assert caught.value.retryable is True


def test_line_breaks_in_the_subject_are_refused(smtp_server: Any) -> None:
    with pytest.raises(NotificationError, match="header injection"):
        _channel(smtp_server).send(
            Notification(subject="ok\r\nBcc: x@evil.example", body="b"), make_secret_store()
        )
    assert smtp_server.messages == []


class _FakeSmtp:
    """Records the calls smtplib.SMTP would receive."""

    instances: ClassVar[list[_FakeSmtp]] = []

    def __init__(self, host: str, port: int, **kwargs: Any) -> None:
        self.host, self.port, self.kwargs = host, port, kwargs
        self.calls: list[tuple[str, object]] = []
        _FakeSmtp.instances.append(self)

    def starttls(self, *, context: ssl.SSLContext) -> None:
        self.calls.append(("starttls", context))

    def login(self, user: str, password: str) -> None:
        self.calls.append(("login", user))

    def send_message(self, message: object, **kwargs: object) -> None:
        self.calls.append(("send", kwargs["to_addrs"]))

    def quit(self) -> None:
        self.calls.append(("quit", None))

    def close(self) -> None:
        self.calls.append(("close", None))


@pytest.mark.parametrize("security", ["starttls", "tls"])
def test_tls_is_verified_by_default(security: str) -> None:
    _FakeSmtp.instances.clear()
    channel = SmtpChannel(
        host="smtp.exemplo.interno",
        security=security,
        sender="a@exemplo.com",
        to=["b@exemplo.com"],
        smtp_factory=_FakeSmtp,  # type: ignore[arg-type]
        smtp_ssl_factory=_FakeSmtp,  # type: ignore[arg-type]
    )
    channel.send(Notification(subject="s", body="b"), make_secret_store())
    (client,) = _FakeSmtp.instances
    context = client.kwargs.get("context") if security == "tls" else client.calls[0][1]
    assert isinstance(context, ssl.SSLContext)
    assert context.verify_mode is ssl.CERT_REQUIRED
    assert context.check_hostname is True
    assert client.port == (465 if security == "tls" else 587)
    assert client.calls[-1] == ("quit", None)


def test_a_failed_starttls_closes_the_connection() -> None:
    class NoTls(_FakeSmtp):
        def starttls(self, *, context: ssl.SSLContext) -> None:
            raise smtplib.SMTPNotSupportedError

    _FakeSmtp.instances.clear()
    channel = SmtpChannel(
        host="smtp.exemplo.interno",
        sender="a@exemplo.com",
        to=["b@exemplo.com"],
        smtp_factory=NoTls,  # type: ignore[arg-type]
    )
    with pytest.raises(NotificationError, match="does not support") as caught:
        channel.send(Notification(subject="s", body="b"), make_secret_store())
    assert caught.value.retryable is False
    assert _FakeSmtp.instances[0].calls == [("close", None)]


def test_an_ambiguous_failure_while_sending_is_not_retried() -> None:
    class Drops(_FakeSmtp):
        def send_message(self, message: object, **kwargs: object) -> None:
            raise smtplib.SMTPServerDisconnected

    channel = SmtpChannel(
        host="smtp.exemplo.interno",
        security="tls",
        sender="a@exemplo.com",
        to=["b@exemplo.com"],
        smtp_ssl_factory=Drops,  # type: ignore[arg-type]
    )
    with pytest.raises(NotificationError, match="send failed") as caught:
        channel.send(Notification(subject="s", body="b"), make_secret_store())
    assert caught.value.retryable is False


@pytest.mark.parametrize(("code", "retryable"), [(451, True), (554, False)])
def test_data_rejections_follow_the_smtp_code(code: int, retryable: bool) -> None:
    class Rejects(_FakeSmtp):
        def send_message(self, message: object, **kwargs: object) -> None:
            raise smtplib.SMTPDataError(code, b"rejected")

    channel = SmtpChannel(
        host="smtp.exemplo.interno",
        security="tls",
        sender="a@exemplo.com",
        to=["b@exemplo.com"],
        smtp_ssl_factory=Rejects,  # type: ignore[arg-type]
    )
    with pytest.raises(NotificationError, match=str(code)) as caught:
        channel.send(Notification(subject="s", body="b"), make_secret_store())
    assert caught.value.retryable is retryable


def test_clear_text_logs_a_warning(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="orchestrator_notifications_smtp"):
        SmtpChannel(host="h", security="none", sender="a@exemplo.com", to=["b@exemplo.com"])
    assert "clear text" in caplog.text


def test_describe_shows_only_the_host() -> None:
    channel = SmtpChannel(host="smtp.exemplo.interno", sender="a@exemplo.com", to=["b@exemplo.com"])
    assert channel.describe() == "smtp://smtp.exemplo.interno:587 (starttls)"


@pytest.mark.parametrize(
    ("settings", "message"),
    [
        ({"sender": "a@exemplo.com", "to": ["b@exemplo.com"]}, "host"),
        ({"host": "h", "sender": "a@exemplo.com", "to": []}, "at least one"),
        ({"host": "h", "sender": "no-at", "to": ["b@exemplo.com"]}, "sender"),
        ({"host": "h", "sender": "a@exemplo.com", "to": "b@exemplo.com"}, "list"),
        ({"host": "h", "sender": "a@exemplo.com", "to": ["b\r\n@x.com"]}, "to"),
        (
            {"host": "h", "sender": "a@exemplo.com", "to": ["b@x.com"], "password": "plain"},
            "reference",
        ),
        (
            {
                "host": "h",
                "sender": "a@x.com",
                "to": ["b@x.com"],
                "username": "u",
                "password": "env:P",
                "token": "env:T",
            },
            "either password or token",
        ),
        ({"host": "h", "sender": "a@x.com", "to": ["b@x.com"], "password": "env:P"}, "username"),
        ({"host": "h", "sender": "a@x.com", "to": ["b@x.com"], "security": "ssl"}, "security"),
        ({"host": "h", "sender": "a@x.com", "to": ["b@x.com"], "timeout": 0}, "timeout"),
        ({"host": "h", "sender": "a@x.com", "to": ["b@x.com"], "typo": 1}, "unknown key"),
    ],
)
def test_invalid_settings_are_refused(settings: dict[str, object], message: str) -> None:
    with pytest.raises(ConfigurationError, match=message):
        SmtpChannel.from_config(ConfigSection(settings, "capabilities.notifications.channels.ops"))


def test_failure_notice_through_the_capability_and_the_outcome_stage(
    smtp_server: Any,
) -> None:
    settings = {
        "capabilities": {
            "notifications": {
                "lifecycle": {"failed": ["ops"]},
                "channels": {
                    "ops": {
                        "provider": "smtp",
                        "host": "127.0.0.1",
                        "port": smtp_server.port,
                        "security": "none",
                        "sender": "automacao@exemplo.com",
                        "to": [RECIPIENT],
                        "timeout": 5,
                    }
                },
            }
        }
    }
    runtime = (
        RuntimeBuilder()
        .with_environment({}, prefix=None)
        .with_settings(settings)
        .with_capability(NotificationCapability, providers={"smtp": SmtpChannel})
        .with_stage(NotifyOutcome(), after="finalize")
        .build()
    )

    def automation(ctx: object) -> None:
        msg = "lote rejeitado"
        raise ValueError(msg)

    result = runtime.run(automation, name="faturamento")
    assert result.status is ExecutionStatus.FAILED
    (raw,) = smtp_server.messages
    message = email.message_from_string(raw, policy=policy.default)
    assert message["Subject"] == "[faturamento] Execução concluída com falha"
    assert "Erro: ValueError: lote rejeitado" in message.get_content()
