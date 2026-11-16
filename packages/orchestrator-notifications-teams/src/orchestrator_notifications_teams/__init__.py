"""Microsoft Teams channel for the notifications Capability of the Orchestrator platform.

Posts to a Workflows webhook with the standard library only (``urllib``).
Register it as a Provider of :class:`~orchestrator_notifications.NotificationCapability`::

    builder.with_capability(NotificationCapability, providers={"teams": TeamsWebhookChannel})
"""

from orchestrator_notifications_teams._channel import TeamsWebhookChannel
from orchestrator_notifications_teams._version import __version__

__all__ = ["TeamsWebhookChannel", "__version__"]
