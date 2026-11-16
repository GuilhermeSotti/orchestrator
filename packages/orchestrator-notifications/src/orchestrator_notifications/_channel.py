"""Port of the notification Providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Self

from orchestrator_core import ConfigSection, SecretStore
from orchestrator_notifications._model import Notification


class NotificationChannel(ABC):
    """A technology that delivers notifications (e-mail, Teams, ...).

    A channel is created once per Runtime from its configuration table and is
    shared by every execution, so it must be thread-safe and keep no execution
    state. Credentials are references in the configuration, resolved at each
    delivery through the ``secrets`` of the execution.
    """

    @classmethod
    @abstractmethod
    def from_config(cls, section: ConfigSection) -> Self:
        """Create the channel from its settings (unknown keys are errors).

        Raises:
            ConfigurationError: If a setting is missing or invalid.
        """

    def verify(self) -> None:  # noqa: B027 - optional hook with a no-op default
        """Check, without sending anything, that the channel can be used."""

    @abstractmethod
    def send(self, notification: Notification, secrets: SecretStore) -> None:
        """Deliver ``notification`` within the channel time limit.

        Raises:
            NotificationError: If it was not delivered. ``retryable`` only when
                nothing was delivered.
        """

    @abstractmethod
    def describe(self) -> str:
        """Return the technology and host, never addresses, URLs or credentials."""
