"""SmtpChannel: e-mail notifications with smtplib and email.message."""

from __future__ import annotations

import hashlib
import logging
import smtplib
import socket
import ssl
from collections.abc import Callable, Sequence
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from typing import ClassVar, Self

from orchestrator_core import ConfigSection, ConfigurationError, SecretRef, SecretStore
from orchestrator_notifications import Notification, NotificationChannel, NotificationError

_logger = logging.getLogger("orchestrator_notifications_smtp")
_SECURITIES = ("starttls", "tls", "none")
_DEFAULT_PORTS = {"starttls": 587, "tls": 465, "none": 25}
_KEYS = (
    "host",
    "port",
    "security",
    "username",
    "password",
    "token",
    "sender",
    "to",
    "cc",
    "timeout",
)
_TRANSIENT_MIN, _TRANSIENT_MAX = 400, 499

SmtpFactory = Callable[..., smtplib.SMTP]


class SmtpChannel(NotificationChannel):
    """E-mail channel over SMTP, built only on the standard library.

    Configuration (``[capabilities.notifications.channels.<name>]``)::

        provider = "smtp"
        host = "smtp.exemplo.interno"
        port = 587  # default: 587 starttls, 465 tls, 25 none
        security = "starttls"  # starttls (default), tls or none
        username = "automacao@exemplo.com"  # with password or token
        password = "env:SMTP_PASSWORD"  # reference; or
        token = "env:SMTP_OAUTH_TOKEN"  # OAuth 2.0 access token (XOAUTH2)
        sender = "automacao@exemplo.com"
        to = ["operacao@exemplo.com"]
        cc = []
        timeout = 10  # seconds

    TLS certificates and host names are verified. ``security = "none"`` sends
    in clear text and logs a warning. A token is used as given: obtaining and
    renewing it is the job of the secret resolver of its scheme.
    """

    name: ClassVar[str] = "smtp"

    def __init__(
        self,
        *,
        host: str,
        sender: str,
        to: Sequence[str],
        port: int | None = None,
        security: str = "starttls",
        username: str | None = None,
        password: SecretRef | str | None = None,
        token: SecretRef | str | None = None,
        cc: Sequence[str] = (),
        timeout: float = 10.0,
        ssl_context: ssl.SSLContext | None = None,
        smtp_factory: SmtpFactory | None = None,
        smtp_ssl_factory: SmtpFactory | None = None,
    ) -> None:
        """Create the channel.

        Args:
            host: SMTP server.
            sender: Address of the ``From`` header.
            to: Recipients (at least one).
            port: Server port; default depends on ``security``.
            security: ``starttls``, ``tls`` or ``none``.
            username: Account for ``password`` or ``token``.
            password: Reference to the password.
            token: Reference to an OAuth 2.0 access token (``XOAUTH2``).
            cc: Copy recipients.
            timeout: Time limit of every network operation, in seconds.
            ssl_context: TLS settings; default: system certificates, verified.
            smtp_factory: Replaces ``smtplib.SMTP`` (tests).
            smtp_ssl_factory: Replaces ``smtplib.SMTP_SSL`` (tests).

        Raises:
            ValueError: If a setting is invalid.
        """
        if security not in _SECURITIES:
            msg = f"security must be one of {', '.join(_SECURITIES)}"
            raise ValueError(msg)
        if not host or any(ch.isspace() for ch in host):
            msg = "host must be a host name or address"
            raise ValueError(msg)
        self._port = _DEFAULT_PORTS[security] if port is None else port
        if not 0 < self._port < 65536:  # noqa: PLR2004 - TCP port range
            msg = "port must be between 1 and 65535"
            raise ValueError(msg)
        if timeout <= 0:
            msg = "timeout must be greater than zero"
            raise ValueError(msg)
        if password is not None and token is not None:
            msg = "use either password or token, not both"
            raise ValueError(msg)
        if (password is not None or token is not None) and not username:
            msg = "username is required with password or token"
            raise ValueError(msg)
        self._host = host
        self._security = security
        self._sender = _address(sender, "sender")
        self._to = tuple(_address(item, "to") for item in to)
        if not self._to:
            msg = "to must name at least one recipient"
            raise ValueError(msg)
        self._cc = tuple(_address(item, "cc") for item in cc)
        self._username = username
        self._password = _reference(password)
        self._token = _reference(token)
        self._timeout = timeout
        self._ssl_context = ssl_context
        self._smtp = smtp_factory or smtplib.SMTP
        self._smtp_ssl = smtp_ssl_factory or smtplib.SMTP_SSL
        if security == "none":
            _logger.warning(
                "SMTP channel %s:%d sends in clear text (security = none)", host, self._port
            )

    @classmethod
    def from_config(cls, section: ConfigSection) -> Self:
        """Create the channel from its configuration table (see the class docs).

        Raises:
            ConfigurationError: If a key is unknown, missing or invalid.
        """
        section.check_keys(_KEYS)
        try:
            return cls(
                host=section.get_str("host"),
                port=section.get_int("port", None, minimum=1, maximum=65535),
                security=section.get_choice("security", _SECURITIES, "starttls"),
                username=section.get_str("username", None),
                password=section.get_secret_ref("password", None),
                token=section.get_secret_ref("token", None),
                sender=section.get_str("sender"),
                to=_strings(section, "to"),
                cc=_strings(section, "cc"),
                timeout=section.get_float("timeout", 10.0, minimum=0.001),
            )
        except ValueError as exc:
            raise ConfigurationError(str(exc), key=section.path) from None

    def describe(self) -> str:
        """Return ``smtp://<host>:<port> (<security>)``."""
        return f"smtp://{self._host}:{self._port} ({self._security})"

    def send(self, notification: Notification, secrets: SecretStore) -> None:
        """Send ``notification`` as a plain text e-mail.

        Raises:
            NotificationError: If the message was not delivered. ``retryable``
                only when it failed before the message was handed to the server.
        """
        message = self._message(notification)
        stage = "connect"
        client: smtplib.SMTP | None = None
        try:
            client = self._connect()
            stage = "authenticate"
            self._authenticate(client, secrets)
            stage = "send"
            client.send_message(message, from_addr=self._sender, to_addrs=[*self._to, *self._cc])
        except smtplib.SMTPAuthenticationError as exc:
            msg = f"SMTP authentication failed (code {exc.smtp_code})"
            raise NotificationError(msg) from None
        except smtplib.SMTPNotSupportedError:
            msg = f"the SMTP server does not support what {stage} needs (STARTTLS or AUTH)"
            raise NotificationError(msg) from None
        except (smtplib.SMTPRecipientsRefused, smtplib.SMTPSenderRefused):
            msg = "the SMTP server refused the sender or the recipients"
            raise NotificationError(msg) from None
        except smtplib.SMTPResponseException as exc:
            transient = _TRANSIENT_MIN <= exc.smtp_code <= _TRANSIENT_MAX
            msg = f"the SMTP server answered {exc.smtp_code} during {stage}"
            raise NotificationError(msg, retryable=transient or stage != "send") from None
        except ssl.SSLCertVerificationError:
            msg = f"the TLS certificate of {self._host} could not be verified"
            raise NotificationError(msg) from None
        except (smtplib.SMTPException, OSError) as exc:
            # Before the message is handed over nothing was delivered; after it,
            # the outcome is unknown and a retry could duplicate the message.
            msg = f"SMTP {stage} failed: {_kind(exc)}"
            raise NotificationError(msg, retryable=stage != "send") from None
        finally:
            if client is not None:
                _quit(client)

    def _message(self, notification: Notification) -> EmailMessage:
        if "\r" in notification.subject or "\n" in notification.subject:
            msg = "the subject has a line break; header injection is refused"
            raise NotificationError(msg)
        message = EmailMessage()
        message["From"] = self._sender
        message["To"] = ", ".join(self._to)
        if self._cc:
            message["Cc"] = ", ".join(self._cc)
        message["Subject"] = notification.subject
        message["Date"] = formatdate(localtime=False)
        message["Message-ID"] = _message_id(notification.dedup_key, self._sender)
        lines = [notification.body.rstrip("\n")]
        if notification.facts:
            lines.append("")
            lines.extend(f"{name}: {value}" for name, value in notification.facts)
        message.set_content("\n".join(lines) + "\n")
        return message

    def _connect(self) -> smtplib.SMTP:
        if self._security == "tls":
            return self._smtp_ssl(
                self._host, self._port, timeout=self._timeout, context=self._context()
            )
        client = self._smtp(self._host, self._port, timeout=self._timeout)
        if self._security == "starttls":
            try:
                client.starttls(context=self._context())
            except BaseException:
                client.close()
                raise
        return client

    def _context(self) -> ssl.SSLContext:
        if self._ssl_context is None:
            self._ssl_context = ssl.create_default_context()
        return self._ssl_context

    def _authenticate(self, client: smtplib.SMTP, secrets: SecretStore) -> None:
        if self._password is not None:
            assert self._username is not None  # noqa: S101 - checked in __init__
            client.login(self._username, secrets.resolve(self._password).reveal())
        elif self._token is not None:
            access = secrets.resolve(self._token).reveal()
            initial = f"user={self._username}\x01auth=Bearer {access}\x01\x01"
            client.ehlo_or_helo_if_needed()
            # On failure the server sends a challenge: the client answers empty.
            client.auth(
                "XOAUTH2",
                lambda challenge=None: initial if challenge is None else "",
                initial_response_ok=True,
            )


def _address(value: str, key: str) -> str:
    text = value.strip()
    local, at, domain = text.partition("@")
    if "\r" in text or "\n" in text or not (local and at and domain) or "@" in domain:
        msg = f"{key} must be an e-mail address"
        raise ValueError(msg)
    return text


def _reference(value: SecretRef | str | None) -> SecretRef | None:
    if value is None or isinstance(value, SecretRef):
        return value
    return SecretRef.parse(value)


def _strings(section: ConfigSection, key: str) -> tuple[str, ...]:
    if key not in section:
        return ()
    value = section[key]
    if not isinstance(value, (list, tuple)) or not all(isinstance(item, str) for item in value):
        raise ConfigurationError("expected a list of e-mail addresses", key=section.key_path(key))
    return tuple(value)


def _message_id(dedup_key: str | None, sender: str) -> str:
    domain = sender.rsplit("@", 1)[1]
    if dedup_key is None:
        return make_msgid(domain=domain)
    digest = hashlib.sha256(dedup_key.encode("utf-8")).hexdigest()[:32]
    return f"<{digest}@{domain}>"


def _kind(error: BaseException) -> str:
    if isinstance(error, (TimeoutError, socket.timeout)):
        return "timed out"
    return type(error).__name__


def _quit(client: smtplib.SMTP) -> None:
    try:
        client.quit()
    except (smtplib.SMTPException, OSError):
        client.close()
