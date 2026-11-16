"""TeamsWebhookChannel: Adaptive Card messages posted to a Teams Workflows webhook."""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any, ClassVar, Self

from orchestrator_core import ConfigSection, ConfigurationError, SecretRef, SecretStore
from orchestrator_notifications import Notification, NotificationChannel, NotificationError

_LOOPBACK = frozenset({"127.0.0.1", "::1", "localhost"})
_RETRYABLE_HTTP = frozenset({429, 502, 503, 504})
_COLORS = {"info": "Default", "warning": "Warning", "error": "Attention"}
_OK_MIN, _OK_MAX = 200, 299

Opener = Callable[..., Any]


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Refuses redirects: the message must never be sent to another address."""

    def redirect_request(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        """Return nothing: urllib then raises HTTPError with the 3xx status."""


class TeamsWebhookChannel(NotificationChannel):
    """Microsoft Teams channel through a Workflows webhook, with the standard library only.

    Configuration (``[capabilities.notifications.channels.<name>]``)::

        provider = "teams"
        webhook = "env:TEAMS_WEBHOOK_URL"  # the URL is a secret: only a reference
        timeout = 10  # seconds

    The message is an Adaptive Card with the subject, the body and the facts.
    The card format follows the Workflows template "post to a channel when a
    webhook request is received"; it still has to be validated against the
    flow of the real environment (RFC-0007, section 6). The URL must use
    ``https`` (``http`` only on the loopback address, for tests); redirects
    are refused, and the URL never appears in errors.
    """

    name: ClassVar[str] = "teams"

    def __init__(
        self, *, webhook: SecretRef | str, timeout: float = 10.0, opener: Opener | None = None
    ) -> None:
        """Create the channel.

        Args:
            webhook: Reference to the webhook URL.
            timeout: Time limit of the request, in seconds.
            opener: Replaces the urllib opener (tests).

        Raises:
            ValueError: If a setting is invalid.
        """
        self._webhook = webhook if isinstance(webhook, SecretRef) else SecretRef.parse(webhook)
        if self._webhook.scheme in {"http", "https"}:
            # "https://..." parses as a reference: refuse the URL written in the configuration.
            msg = "webhook must be a secret reference such as 'env:TEAMS_WEBHOOK_URL', not the URL"
            raise ValueError(msg)
        if timeout <= 0:
            msg = "timeout must be greater than zero"
            raise ValueError(msg)
        self._timeout = timeout
        self._open = opener or urllib.request.build_opener(_NoRedirect).open

    @classmethod
    def from_config(cls, section: ConfigSection) -> Self:
        """Create the channel from ``webhook`` and ``timeout``.

        Raises:
            ConfigurationError: If a key is unknown, missing or invalid.
        """
        section.check_keys(("webhook", "timeout"))
        try:
            return cls(
                webhook=section.get_secret_ref("webhook"),
                timeout=section.get_float("timeout", 10.0, minimum=0.001),
            )
        except ValueError as exc:
            raise ConfigurationError(str(exc), key=section.path) from None

    def describe(self) -> str:
        """Return ``teams-webhook``; the URL is a secret."""
        return "teams-webhook"

    def send(self, notification: Notification, secrets: SecretStore) -> None:
        """Post ``notification`` as an Adaptive Card.

        Raises:
            NotificationError: If it was not accepted. ``retryable`` when the
                request did not reach the webhook or was refused with 429,
                502, 503 or 504.
        """
        url = secrets.resolve(self._webhook).reveal()
        parts = urllib.parse.urlsplit(url)
        secure = parts.scheme == "https" or (parts.scheme == "http" and parts.hostname in _LOOPBACK)
        if not secure or not parts.hostname:
            msg = "the Teams webhook URL must use https"
            raise NotificationError(msg)
        body = json.dumps(card(notification), ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(  # noqa: S310 - scheme checked above
            url,
            data=body,
            method="POST",
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        try:
            with self._open(request, timeout=self._timeout) as response:
                status = int(response.status)
        except urllib.error.HTTPError as exc:
            exc.close()
            msg = f"the Teams webhook answered HTTP {exc.code}"
            raise NotificationError(msg, retryable=exc.code in _RETRYABLE_HTTP) from None
        except urllib.error.URLError as exc:
            # The connection was not established: nothing was delivered.
            msg = f"the Teams webhook is unreachable ({_kind(exc.reason)})"
            raise NotificationError(msg, retryable=True) from None
        except OSError as exc:
            # The request may have been received: a retry could duplicate it.
            msg = f"the Teams webhook did not answer ({_kind(exc)})"
            raise NotificationError(msg) from None
        if not _OK_MIN <= status <= _OK_MAX:
            msg = f"the Teams webhook answered HTTP {status}"
            raise NotificationError(msg)


def card(notification: Notification) -> dict[str, object]:
    """Return the Workflows webhook message (an Adaptive Card) of ``notification``.

    Example:
        >>> payload = card(Notification(subject="Lote", body="ok", facts=(("Itens", "3"),)))
        >>> payload["attachments"][0]["contentType"]
        'application/vnd.microsoft.card.adaptive'
    """
    blocks: list[dict[str, object]] = [
        {
            "type": "TextBlock",
            "text": notification.subject,
            "weight": "Bolder",
            "size": "Medium",
            "wrap": True,
            "color": _COLORS[notification.severity.value],
        },
        {"type": "TextBlock", "text": notification.body, "wrap": True},
    ]
    if notification.facts:
        blocks.append(
            {
                "type": "FactSet",
                "facts": [{"title": name, "value": value} for name, value in notification.facts],
            }
        )
    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": blocks,
                },
            }
        ],
    }


def _kind(error: object) -> str:
    if isinstance(error, (TimeoutError, socket.timeout)):
        return "timed out"
    if isinstance(error, BaseException):
        return type(error).__name__
    return "network error"
