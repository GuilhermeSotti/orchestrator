from __future__ import annotations

import json
from typing import Any

import pytest

from orchestrator_core import ConfigSection, ConfigurationError, SecretResolver
from orchestrator_core.testing import make_secret_store
from orchestrator_notifications import (
    Notification,
    NotificationChannel,
    NotificationError,
    Severity,
)
from orchestrator_notifications.testing import NotificationChannelContract
from orchestrator_notifications_teams import TeamsWebhookChannel
from orchestrator_notifications_teams._channel import card

SENTINEL = "S3NT1NEL-teams-webhook-77ab"


class _Urls:
    def __init__(self, urls: dict[str, str]) -> None:
        self.urls = urls

    def resolve(self, target: str) -> str:
        return self.urls[target]


def _store(**urls: str) -> Any:
    return make_secret_store({"test": _Urls(urls)})


class TestTeamsContract(NotificationChannelContract):
    @pytest.fixture(autouse=True)
    def _server(self, webhook: Any) -> None:
        self.server = webhook

    def make_channel(self) -> NotificationChannel:
        return TeamsWebhookChannel(webhook="test:url", timeout=5)

    def received(self) -> list[str]:
        return list(self.server.bodies)

    def make_failing_channel(self) -> NotificationChannel:
        self.server.status = 400
        return TeamsWebhookChannel(webhook="test:url", timeout=5)

    def make_unresponsive_channel(self, timeout: float) -> NotificationChannel:
        self.server.silent = True
        return TeamsWebhookChannel(webhook="test:url", timeout=timeout)

    def secret_resolvers(self) -> dict[str, SecretResolver]:
        return {"test": _Urls({"url": self.server.url(f"/workflows/{SENTINEL}")})}

    def private_values(self) -> list[str]:
        return [SENTINEL]


def test_the_message_is_an_adaptive_card(webhook: Any) -> None:
    channel = TeamsWebhookChannel(webhook="test:url")
    note = Notification(
        subject="Execução concluída com falha",
        body="Informamos que falhou.",
        severity=Severity.ERROR,
        facts=(("Erro", "ValueError: lote"),),
    )
    channel.send(note, _store(url=webhook.url("/hook")))
    (raw,) = webhook.bodies
    payload = json.loads(raw)
    assert payload == card(note)
    content = payload["attachments"][0]["content"]
    title, text, facts = content["body"]
    assert (title["text"], title["color"]) == ("Execução concluída com falha", "Attention")
    assert text["text"] == "Informamos que falhou."
    assert facts["facts"] == [{"title": "Erro", "value": "ValueError: lote"}]
    assert "Execução" in raw  # sent as UTF-8, not escaped


@pytest.mark.parametrize(
    ("status", "retryable"), [(400, False), (500, False), (503, True), (429, True)]
)
def test_http_errors_follow_the_status(webhook: Any, status: int, retryable: bool) -> None:
    webhook.status = status
    with pytest.raises(NotificationError, match=f"HTTP {status}") as caught:
        TeamsWebhookChannel(webhook="test:url").send(
            Notification(subject="s", body="b"), _store(url=webhook.url(f"/w/{SENTINEL}"))
        )
    assert caught.value.retryable is retryable
    assert SENTINEL not in str(caught.value)


def test_redirects_are_refused(webhook: Any) -> None:
    webhook.redirect_to = webhook.url("/elsewhere")
    with pytest.raises(NotificationError, match="HTTP 302"):
        TeamsWebhookChannel(webhook="test:url").send(
            Notification(subject="s", body="b"), _store(url=webhook.url("/hook"))
        )
    assert webhook.paths == ["/hook"]  # the redirect target was never called


def test_plain_http_is_refused_outside_the_loopback() -> None:
    with pytest.raises(NotificationError, match="https") as caught:
        TeamsWebhookChannel(webhook="test:url").send(
            Notification(subject="s", body="b"), _store(url=f"http://example.com/{SENTINEL}")
        )
    assert SENTINEL not in str(caught.value)
    with pytest.raises(NotificationError, match="https"):
        TeamsWebhookChannel(webhook="test:url").send(
            Notification(subject="s", body="b"), _store(url="file:///etc/passwd")
        )


def test_an_unreachable_webhook_is_retryable_and_hides_the_url() -> None:
    import socket

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    with pytest.raises(NotificationError, match="unreachable") as caught:
        TeamsWebhookChannel(webhook="test:url", timeout=2).send(
            Notification(subject="s", body="b"), _store(url=f"http://127.0.0.1:{port}/{SENTINEL}")
        )
    assert caught.value.retryable is True
    assert SENTINEL not in str(caught.value)
    assert caught.value.__cause__ is None


def test_no_answer_is_ambiguous_and_not_retried(webhook: Any) -> None:
    webhook.silent = True
    with pytest.raises(NotificationError, match="did not answer") as caught:
        TeamsWebhookChannel(webhook="test:url", timeout=0.5).send(
            Notification(subject="s", body="b"), _store(url=webhook.url("/hook"))
        )
    assert caught.value.retryable is False


@pytest.mark.parametrize(
    ("settings", "message"),
    [
        ({}, "required key is missing"),
        ({"webhook": "https://example.com/hook"}, "not the URL"),
        ({"webhook": "plain-text"}, "secret reference"),
        ({"webhook": "env:URL", "timeout": 0}, "timeout"),
        ({"webhook": "env:URL", "extra": 1}, "unknown key"),
    ],
)
def test_invalid_settings_are_refused(settings: dict[str, object], message: str) -> None:
    with pytest.raises(ConfigurationError, match=message):
        TeamsWebhookChannel.from_config(
            ConfigSection(settings, "capabilities.notifications.channels.t")
        )


def test_describe_never_shows_the_url() -> None:
    assert TeamsWebhookChannel(webhook="env:TEAMS").describe() == "teams-webhook"
