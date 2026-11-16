"""Errors of the notifications Capability."""

from __future__ import annotations

from orchestrator_core import ProviderError


class NotificationError(ProviderError):
    """A notification could not be delivered.

    Providers raise it instead of letting library exceptions escape. The
    message never contains recipients, URLs, credentials or other secret
    values. ``retryable`` is true only when the Provider knows that nothing
    was delivered, so that a retry cannot duplicate the message.
    """
