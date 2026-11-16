"""E-mail (SMTP) channel for the notifications Capability of the Orchestrator platform.

Built only on the standard library (``smtplib`` and ``email.message``).
Register it as a Provider of :class:`~orchestrator_notifications.NotificationCapability`::

    builder.with_capability(NotificationCapability, providers={"smtp": SmtpChannel})
"""

from orchestrator_notifications_smtp._channel import SmtpChannel
from orchestrator_notifications_smtp._version import __version__

__all__ = ["SmtpChannel", "__version__"]
