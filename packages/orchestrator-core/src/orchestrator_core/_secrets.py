"""Secrets: references in configuration, values resolved only at use time.

Configuration never holds secret values. It holds references such as
``env:DB_PASSWORD`` or ``file:/run/secrets/db``, which are resolved through a
:class:`SecretResolver` registered for the scheme. Resolved values are wrapped
in :class:`Secret`, which never reveals itself in ``repr``, ``str`` or
formatting, and are registered for masking in logs, events and records.
"""

from __future__ import annotations

import hmac
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn, Protocol, runtime_checkable

from orchestrator_core._errors import SecretResolutionError
from orchestrator_core._redaction import MASK, Redactor

_SCHEME_RE = re.compile(r"^([a-z][a-z0-9+.-]*):(.+)$", re.DOTALL)


class Secret:
    """A resolved secret value.

    The value is only available through :meth:`reveal`. Instances cannot be
    pickled and compare in constant time.

    Example:
        >>> secret = Secret("s3cr3t-value")
        >>> secret
        Secret('***')
        >>> f"{secret}"
        '***'
    """

    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        """Wrap ``value``."""
        self._value = value

    def reveal(self) -> str:
        """Return the secret value. Never log or persist the result."""
        return self._value

    def __repr__(self) -> str:
        """Return a masked representation."""
        return f"Secret('{MASK}')"

    def __str__(self) -> str:
        """Return the mask."""
        return MASK

    def __format__(self, format_spec: str) -> str:
        """Return the mask, whatever the format specification."""
        return MASK

    def __eq__(self, other: object) -> bool:
        """Compare two secrets in constant time."""
        if not isinstance(other, Secret):
            return NotImplemented
        return hmac.compare_digest(self._value.encode(), other._value.encode())

    __hash__ = None  # type: ignore[assignment]

    def __reduce__(self) -> NoReturn:
        """Refuse serialization."""
        msg = "Secret values cannot be pickled"
        raise TypeError(msg)


@dataclass(frozen=True, slots=True)
class SecretRef:
    """Reference to a secret, written as ``<scheme>:<target>``.

    Attributes:
        scheme: Resolver scheme, such as ``env`` or ``file``.
        target: Scheme-specific locator, such as a variable name or a path.
    """

    scheme: str
    target: str

    @classmethod
    def parse(cls, text: str) -> SecretRef:
        """Parse ``<scheme>:<target>``.

        Raises:
            ValueError: If ``text`` is not a reference. The message never
                contains ``text``, which could be a literal secret.
        """
        match = _SCHEME_RE.match(text.strip())
        if match is None:
            msg = "expected a secret reference such as 'env:NAME' or 'file:/path'"
            raise ValueError(msg)
        return cls(scheme=match.group(1), target=match.group(2))

    def __str__(self) -> str:
        """Return the reference in ``<scheme>:<target>`` form."""
        return f"{self.scheme}:{self.target}"


@runtime_checkable
class SecretResolver(Protocol):
    """Port that resolves the target of a secret reference into its value.

    Implementations raise :class:`SecretResolutionError` with a message that
    identifies the target but never the value.
    """

    def resolve(self, target: str) -> str:
        """Return the secret value for ``target``."""
        ...


class EnvSecretResolver:
    """Resolves ``env:NAME`` from environment variables."""

    def __init__(self, environ: Mapping[str, str] | None = None) -> None:
        """Create the resolver.

        Args:
            environ: Mapping to read from. Defaults to :data:`os.environ`.
        """
        self._environ = environ

    def resolve(self, target: str) -> str:
        """Return the value of the environment variable ``target``."""
        environ = os.environ if self._environ is None else self._environ
        try:
            return environ[target]
        except KeyError:
            msg = f"environment variable {target!r} is not set"
            raise SecretResolutionError(msg) from None


class FileSecretResolver:
    """Resolves ``file:PATH`` by reading a UTF-8 file, without its final newline."""

    def resolve(self, target: str) -> str:
        """Return the content of the file at ``target``."""
        try:
            return Path(target).read_text(encoding="utf-8").rstrip("\r\n")
        except OSError as exc:
            msg = f"cannot read secret file {target!r}: {exc.strerror or type(exc).__name__}"
            raise SecretResolutionError(msg) from None


class SecretStore:
    """Resolves secret references through the resolvers registered by scheme."""

    def __init__(self, resolvers: Mapping[str, SecretResolver], redactor: Redactor) -> None:
        """Create the store.

        Args:
            resolvers: Resolver for each scheme.
            redactor: Registry that receives every resolved value for masking.
        """
        self._resolvers = dict(resolvers)
        self._redactor = redactor

    @property
    def schemes(self) -> tuple[str, ...]:
        """Schemes that can be resolved."""
        return tuple(sorted(self._resolvers))

    def resolve(self, reference: SecretRef | str) -> Secret:
        """Resolve ``reference`` and register its value for masking.

        Args:
            reference: A :class:`SecretRef` or its ``<scheme>:<target>`` text.

        Raises:
            SecretResolutionError: If the reference is malformed, the scheme is
                unknown or the resolver fails.
        """
        if isinstance(reference, str):
            try:
                reference = SecretRef.parse(reference)
            except ValueError as exc:
                raise SecretResolutionError(str(exc)) from None
        resolver = self._resolvers.get(reference.scheme)
        if resolver is None:
            msg = f"no secret resolver registered for scheme {reference.scheme!r}"
            raise SecretResolutionError(msg)
        try:
            value: object = resolver.resolve(reference.target)
        except SecretResolutionError:
            raise
        except Exception as exc:  # noqa: BLE001 - never let resolver details escape
            msg = f"secret resolver for scheme {reference.scheme!r} failed: {type(exc).__name__}"
            raise SecretResolutionError(msg) from None
        if not isinstance(value, str):
            msg = f"secret resolver for scheme {reference.scheme!r} returned a non-string value"
            raise SecretResolutionError(msg)
        self._redactor.register(value)
        return Secret(value)
