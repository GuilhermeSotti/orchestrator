"""Capability contract, compatibility check and registry."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar, Self

from orchestrator_core._errors import (
    CapabilityError,
    CapabilityNotFoundError,
    DuplicateCapabilityError,
    IncompatibleCapabilityError,
)
from orchestrator_core._version import CORE_API_VERSION

if TYPE_CHECKING:
    from orchestrator_core._config import ConfigSection
    from orchestrator_core._context import ExecutionContext

_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_API_RE = re.compile(r"^(\d+)\.(\d+)$")


class Capability[HandleT](ABC):
    """Contract of a Capability: a Runtime-scoped factory of execution-scoped handles.

    A Capability is registered once in a Runtime and shared by every execution,
    so it must be thread-safe and must not keep execution state. For each
    execution, the ``provision_dependencies`` stage calls :meth:`verify` and
    :meth:`open`; the handle returned by :meth:`open` is what automations obtain
    from :meth:`ExecutionContext.capability`. Cleanups are registered in
    ``ctx.resources`` and run during ``finalize``.

    Subclasses define :attr:`default_name` and, when they accept configuration,
    override :meth:`from_config`.

    Example:
        >>> class Greeter(Capability[str]):
        ...     default_name = "greeter"
        ...
        ...     def open(self, ctx):
        ...         return f"hello from {ctx.execution_id}"

    Attributes:
        default_name: Registration name and configuration table
            (``[capabilities.<name>]``) used when no name is given.
        core_api: Core API version (``"major.minor"``) the Capability was built
            against. When set, registration fails if it is incompatible.
    """

    default_name: ClassVar[str]
    core_api: ClassVar[str | None] = None

    @classmethod
    def from_config(cls, section: ConfigSection, /, **options: Any) -> Self:  # noqa: ANN401
        """Create the Capability from its configuration table.

        The default implementation accepts no settings and passes ``options`` to
        the constructor.

        Raises:
            ConfigurationError: If the table has unknown or invalid keys.
        """
        section.check_keys(())
        return cls(**options)

    def verify(self) -> None:  # noqa: B027 - optional hook with a no-op default
        """Check that the Capability can be used; raise ``CapabilityUnavailableError`` if not."""

    @abstractmethod
    def open(self, ctx: ExecutionContext) -> HandleT:
        """Acquire the handle used by one execution.

        Register every cleanup in ``ctx.resources``; register outcome-dependent
        actions (such as commit or rollback) with ``ctx.add_finalizer``.
        """


def is_api_compatible(required: str, current: str = CORE_API_VERSION) -> bool:
    """Tell whether a Capability built against ``required`` works with ``current``.

    Before 1.0 the ``major.minor`` must match exactly; from 1.0 on the major must
    match and the required minor must not be newer than the current one.

    Raises:
        ValueError: If a version is not in ``major.minor`` form.
    """
    required_match, current_match = _API_RE.match(required), _API_RE.match(current)
    if required_match is None or current_match is None:
        msg = "API versions must have the form 'major.minor'"
        raise ValueError(msg)
    req_major, req_minor = int(required_match.group(1)), int(required_match.group(2))
    cur_major, cur_minor = int(current_match.group(1)), int(current_match.group(2))
    if cur_major == 0 or req_major == 0:
        return (req_major, req_minor) == (cur_major, cur_minor)
    return req_major == cur_major and req_minor <= cur_minor


@dataclass(frozen=True, slots=True)
class CapabilityRegistration:
    """A Capability registered under a name."""

    name: str
    capability: Capability[Any]


class CapabilityRegistry:
    """Immutable set of Capabilities of a Runtime, in registration order."""

    def __init__(self, registrations: Sequence[CapabilityRegistration] = ()) -> None:
        """Validate and store ``registrations``.

        Raises:
            CapabilityError: If a name is invalid or an object is not a Capability.
            DuplicateCapabilityError: If two registrations share a name.
            IncompatibleCapabilityError: If a Capability requires another Core API.
        """
        by_name: dict[str, CapabilityRegistration] = {}
        for registration in registrations:
            self._validate(registration)
            if registration.name in by_name:
                msg = f"a capability named {registration.name!r} is already registered"
                raise DuplicateCapabilityError(msg)
            by_name[registration.name] = registration
        self._registrations = tuple(registrations)
        self._by_name = by_name

    @property
    def registrations(self) -> tuple[CapabilityRegistration, ...]:
        """Registrations in registration order."""
        return self._registrations

    @property
    def names(self) -> tuple[str, ...]:
        """Registered names in registration order."""
        return tuple(registration.name for registration in self._registrations)

    def __len__(self) -> int:
        """Return the number of registrations."""
        return len(self._registrations)

    def find[H](self, key: type[Capability[H]], name: str | None = None) -> CapabilityRegistration:
        """Find the registration of type ``key`` (and ``name``, when given).

        Raises:
            CapabilityNotFoundError: If nothing matches.
            CapabilityError: If several registrations match and no name is given.
        """
        if name is not None:
            registration = self._by_name.get(name)
            if registration is None or not isinstance(registration.capability, key):
                msg = f"no capability of type {key.__name__} is registered as {name!r}"
                raise CapabilityNotFoundError(msg)
            return registration
        matches = [r for r in self._registrations if isinstance(r.capability, key)]
        if not matches:
            msg = f"no capability of type {key.__name__} is registered"
            raise CapabilityNotFoundError(msg)
        if len(matches) > 1:
            names = ", ".join(repr(r.name) for r in matches)
            msg = (
                f"several capabilities of type {key.__name__} are registered ({names}); pass name="
            )
            raise CapabilityError(msg)
        return matches[0]

    @staticmethod
    def _validate(registration: CapabilityRegistration) -> None:
        candidate: object = registration.capability
        if not isinstance(candidate, Capability):
            msg = f"{type(candidate).__name__} is not a Capability"
            raise CapabilityError(msg)
        capability = candidate
        if not _NAME_RE.match(registration.name):
            msg = (
                f"invalid capability name {registration.name!r}: use lowercase letters, "
                "digits and '_' (at most 64 characters), starting with a letter"
            )
            raise CapabilityError(msg)
        required = type(capability).core_api
        if required is not None:
            try:
                compatible = is_api_compatible(required)
            except ValueError:
                compatible = False
            if not compatible:
                msg = (
                    f"capability {registration.name!r} ({type(capability).__qualname__}) "
                    f"requires Core API {required}, but this Core provides {CORE_API_VERSION}"
                )
                raise IncompatibleCapabilityError(msg)
