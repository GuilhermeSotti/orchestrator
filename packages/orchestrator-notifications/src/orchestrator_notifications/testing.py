"""In-memory channel and the conformance suite of notification channel Providers (D-21).

Subclass :class:`NotificationChannelContract` in the Provider's tests and
implement :meth:`~NotificationChannelContract.make_channel` and
:meth:`~NotificationChannelContract.received`; pytest collects the inherited
``test_*`` methods. Nothing here imports pytest.

Example::

    class TestSmtpContract(NotificationChannelContract):
        def make_channel(self) -> NotificationChannel:
            return SmtpChannel(host="127.0.0.1", port=self.server.port, security="none", ...)

        def received(self) -> list[str]:
            return self.server.messages
"""

from __future__ import annotations

import threading
import time
from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Self

from orchestrator_core import ConfigSection, SecretResolver, SecretStore
from orchestrator_core.testing import check_capability_conformance, make_secret_store
from orchestrator_notifications._capability import NotificationCapability
from orchestrator_notifications._channel import NotificationChannel
from orchestrator_notifications._errors import NotificationError
from orchestrator_notifications._model import DeliveryStatus, Notification
from orchestrator_notifications._notifier import Notifier

__all__ = ["InMemoryChannel", "NotificationChannelContract"]


class InMemoryChannel(NotificationChannel):
    """Channel that keeps notifications in memory, for tests and examples.

    Configuration keys: ``fail`` (number of first deliveries that fail,
    default 0) and ``retryable`` (whether those failures are retryable,
    default false).

    Example:
        >>> channel = InMemoryChannel()
        >>> channel.send(Notification(subject="Olá", body="corpo"), None)  # type: ignore[arg-type]
        >>> [n.subject for n in channel.sent]
        ['Olá']
    """

    def __init__(self, *, fail: int = 0, retryable: bool = False) -> None:
        """Create the channel; the first ``fail`` deliveries raise NotificationError."""
        if fail < 0:
            msg = "fail must be zero or greater"
            raise ValueError(msg)
        self._remaining = fail
        self._retryable = retryable
        self._sent: list[Notification] = []
        self._lock = threading.Lock()

    @classmethod
    def from_config(cls, section: ConfigSection) -> Self:
        """Create the channel from ``fail`` and ``retryable``."""
        section.check_keys(("fail", "retryable"))
        return cls(
            fail=section.get_int("fail", 0, minimum=0),
            retryable=section.get_bool("retryable", False),
        )

    @property
    def sent(self) -> tuple[Notification, ...]:
        """Notifications delivered so far, in order."""
        with self._lock:
            return tuple(self._sent)

    def send(self, notification: Notification, secrets: SecretStore) -> None:  # noqa: ARG002
        """Keep ``notification``, or fail while failures remain."""
        with self._lock:
            if self._remaining > 0:
                self._remaining -= 1
                msg = "the in-memory channel refused the notification"
                raise NotificationError(msg, retryable=self._retryable)
            self._sent.append(notification)

    def describe(self) -> str:
        """Return ``memory``."""
        return "memory"


class NotificationChannelContract(ABC):
    """Behavior every :class:`NotificationChannel` must show, as inheritable tests."""

    @abstractmethod
    def make_channel(self) -> NotificationChannel:
        """Return a channel that delivers to the test endpoint."""

    @abstractmethod
    def received(self) -> list[str]:
        """Return the text of every message the test endpoint received, in order."""

    def make_failing_channel(self) -> NotificationChannel | None:
        """Return a channel whose endpoint refuses deliveries (``None`` skips the test)."""
        return None

    def make_unresponsive_channel(self, timeout: float) -> NotificationChannel | None:
        """Return a channel whose endpoint never answers (``None`` skips the test).

        Args:
            timeout: Time limit to configure in the channel, in seconds.
        """
        del timeout
        return None

    def secret_resolvers(self) -> Mapping[str, SecretResolver]:
        """Return the resolvers needed by the test configuration (``env:`` and ``file:`` exist)."""
        return {}

    def private_values(self) -> list[str]:
        """Return values that must never appear in ``describe()`` or in errors.

        Secrets and addresses of the test configuration.
        """
        return []

    def secrets(self) -> SecretStore:
        """Return a secret store with :meth:`secret_resolvers`."""
        return make_secret_store(self.secret_resolvers())

    def test_send_delivers_subject_body_and_facts(self) -> None:
        """The endpoint receives the subject, the body and the facts."""
        notification = Notification(
            subject="Contract subject 7c1",
            body="Contract body line",
            facts=(("Lote", "42-contract"),),
            kind="contract.check",
            dedup_key="contract-1",
        )
        self.make_channel().send(notification, self.secrets())
        text = "\n".join(self.received())
        for expected in ("Contract subject 7c1", "Contract body line", "42-contract"):
            assert expected in text, expected  # noqa: S101

    def test_describe_has_no_private_values(self) -> None:
        """``describe()`` shows neither secrets nor addresses."""
        description = self.make_channel().describe()
        assert description  # noqa: S101
        for value in self.private_values():
            assert value not in description  # noqa: S101

    def test_failures_are_translated_without_private_values(self) -> None:
        """A refused delivery raises NotificationError without private values."""
        channel = self.make_failing_channel()
        if channel is None:
            return
        error: NotificationError | None = None
        try:
            channel.send(Notification(subject="Refused", body="body"), self.secrets())
        except NotificationError as exc:
            error = exc
        if error is None:
            msg = "the failing channel reported a delivery"
            raise AssertionError(msg)
        assert isinstance(error.retryable, bool)  # noqa: S101
        for value in self.private_values():
            assert value not in str(error)  # noqa: S101

    def test_time_limit_is_respected(self) -> None:
        """An endpoint that never answers fails within the time limit."""
        channel = self.make_unresponsive_channel(0.5)
        if channel is None:
            return
        begin = time.monotonic()
        try:
            channel.send(Notification(subject="Stuck", body="body"), self.secrets())
        except NotificationError:
            pass
        else:
            msg = "the unresponsive channel reported a delivery"
            raise AssertionError(msg)
        assert time.monotonic() - begin < 5.0  # noqa: S101

    def test_capability_conformance(self) -> None:
        """The Capability with this channel honors the Capability contract."""
        capability = NotificationCapability(
            {"contract": self.make_channel()}, default_channels=["contract"]
        )

        def use(notifier: Notifier) -> None:
            (report,) = notifier.send(Notification(subject="Conformance", body="ok"))
            assert report.status is DeliveryStatus.SENT, report  # noqa: S101

        check_capability_conformance(capability, use=use, secret_resolvers=self.secret_resolvers())
