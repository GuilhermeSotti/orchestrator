"""Configuration: sources, precedence, validation and typed access.

Precedence, from lowest to highest: built-in defaults, TOML file, environment
variables, explicit settings passed to the builder. The merged result is
immutable and validated when the Runtime is built.

Layout::

    [runtime]  # settings of the Runtime itself
    name = "billing"
    timeout = 300.0

    [capabilities.sql]  # one table per registered Capability
    provider = "sqlite"

    [app]  # any other table belongs to the consumer project

Environment variables use a prefix and ``__`` between path segments:
``ORCHESTRATOR_RUNTIME__TIMEOUT=30`` sets ``runtime.timeout``. Only variables
with at least one ``__`` are read.
"""

from __future__ import annotations

import enum
import math
import os
import re
import tomllib
from collections.abc import Collection, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Final, overload

from orchestrator_core._errors import ConfigurationError
from orchestrator_core._secrets import SecretRef

_TRUE: Final = frozenset({"true", "1", "yes", "on"})
_FALSE: Final = frozenset({"false", "0", "no", "off"})
_RUNTIME_NAME_RE: Final = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_ENV_SEGMENT_RE: Final = re.compile(r"^[a-z0-9_]+$")
RESERVED_SECTIONS: Final = ("runtime", "capabilities")
"""Top-level tables owned by the Core. Every other table belongs to the consumer."""


class _Missing(enum.Enum):
    MISSING = enum.auto()


_MISSING: Final = _Missing.MISSING


def _freeze(value: object) -> object:
    if isinstance(value, Mapping):
        return MappingProxyType({str(k): _freeze(v) for k, v in value.items()})
    if isinstance(value, list | tuple):
        return tuple(_freeze(v) for v in value)
    return value


def _thaw(value: object) -> object:
    if isinstance(value, Mapping):
        return {k: _thaw(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_thaw(v) for v in value]
    return value


def _join(path: str, key: str) -> str:
    return f"{path}.{key}" if path else key


class ConfigSection(Mapping[str, object]):
    """Immutable view of a configuration table, with typed accessors.

    Values coming from environment variables are strings; the typed accessors
    convert them. Every error names the full dotted key.

    Example:
        >>> section = ConfigSection({"timeout": "2.5", "read_only": "true"}, "capabilities.sql")
        >>> section.get_float("timeout")
        2.5
        >>> section.get_bool("read_only")
        True
        >>> section.get_int("pool_size", 4)
        4
    """

    __slots__ = ("_data", "_path")

    def __init__(self, data: Mapping[str, object], path: str = "") -> None:
        """Create a view over ``data``.

        Args:
            data: Table content. It is deep-copied and frozen.
            path: Dotted path of the table, used in error messages.
        """
        frozen = _freeze(data)
        assert isinstance(frozen, Mapping)  # noqa: S101 - invariant of _freeze
        self._data: Mapping[str, object] = frozen
        self._path = path

    @property
    def path(self) -> str:
        """Dotted path of this table (empty for the root)."""
        return self._path

    def __getitem__(self, key: str) -> object:
        """Return the raw value of ``key``."""
        return self._data[key]

    def __iter__(self) -> Iterator[str]:
        """Iterate over keys."""
        return iter(self._data)

    def __len__(self) -> int:
        """Return the number of keys."""
        return len(self._data)

    def __repr__(self) -> str:
        """Return the path and keys; values are omitted."""
        return f"ConfigSection(path={self._path!r}, keys={sorted(self._data)!r})"

    def key_path(self, key: str) -> str:
        """Return the full dotted path of ``key``."""
        return _join(self._path, key)

    def to_dict(self) -> dict[str, object]:
        """Return a mutable deep copy of the table."""
        thawed = _thaw(self._data)
        assert isinstance(thawed, dict)  # noqa: S101 - invariant of _thaw
        return thawed

    def check_keys(self, allowed: Iterable[str]) -> None:
        """Reject keys outside ``allowed`` (catches typos).

        Raises:
            ConfigurationError: If an unknown key is present.
        """
        unknown = sorted(set(self._data) - set(allowed))
        if unknown:
            msg = f"unknown key(s): {', '.join(unknown)}"
            raise ConfigurationError(msg, key=self._path or "<root>")

    def section(self, key: str) -> ConfigSection:
        """Return the nested table ``key`` (empty if absent).

        Raises:
            ConfigurationError: If ``key`` exists and is not a table.
        """
        value = self._data.get(key)
        if value is None:
            return ConfigSection({}, self.key_path(key))
        if not isinstance(value, Mapping):
            raise ConfigurationError("expected a table", key=self.key_path(key))
        return ConfigSection(value, self.key_path(key))

    @overload
    def get_str(self, key: str) -> str: ...
    @overload
    def get_str[D](self, key: str, default: D) -> str | D: ...
    def get_str(self, key: str, default: object = _MISSING) -> object:
        """Return a string value.

        Raises:
            ConfigurationError: If missing without default, or not a string.
        """
        raw = self._raw(key, default)
        if raw is default:
            return default
        if not isinstance(raw, str):
            raise ConfigurationError("expected a string", key=self.key_path(key))
        return raw

    @overload
    def get_int(
        self, key: str, *, minimum: int | None = None, maximum: int | None = None
    ) -> int: ...
    @overload
    def get_int[D](
        self,
        key: str,
        default: D,
        *,
        minimum: int | None = None,
        maximum: int | None = None,
    ) -> int | D: ...
    def get_int(
        self,
        key: str,
        default: object = _MISSING,
        *,
        minimum: int | None = None,
        maximum: int | None = None,
    ) -> object:
        """Return an integer value, optionally within ``[minimum, maximum]``.

        Raises:
            ConfigurationError: If missing without default, invalid or out of range.
        """
        raw = self._raw(key, default)
        if raw is default:
            return default
        if isinstance(raw, bool) or not isinstance(raw, int | str):
            raise ConfigurationError("expected an integer", key=self.key_path(key))
        try:
            value = int(raw)
        except ValueError:
            raise ConfigurationError("expected an integer", key=self.key_path(key)) from None
        self._check_range(key, value, minimum, maximum)
        return value

    @overload
    def get_float(
        self, key: str, *, minimum: float | None = None, maximum: float | None = None
    ) -> float: ...
    @overload
    def get_float[D](
        self,
        key: str,
        default: D,
        *,
        minimum: float | None = None,
        maximum: float | None = None,
    ) -> float | D: ...
    def get_float(
        self,
        key: str,
        default: object = _MISSING,
        *,
        minimum: float | None = None,
        maximum: float | None = None,
    ) -> object:
        """Return a number as ``float``, optionally within ``[minimum, maximum]``.

        Raises:
            ConfigurationError: If missing without default, invalid or out of range.
        """
        raw = self._raw(key, default)
        if raw is default:
            return default
        if isinstance(raw, bool) or not isinstance(raw, int | float | str):
            raise ConfigurationError("expected a number", key=self.key_path(key))
        try:
            value = float(raw)
        except ValueError:
            raise ConfigurationError("expected a number", key=self.key_path(key)) from None
        if not math.isfinite(value):
            raise ConfigurationError("expected a finite number", key=self.key_path(key))
        self._check_range(key, value, minimum, maximum)
        return value

    @overload
    def get_bool(self, key: str) -> bool: ...
    @overload
    def get_bool[D](self, key: str, default: D) -> bool | D: ...
    def get_bool(self, key: str, default: object = _MISSING) -> object:
        """Return a boolean; accepts the strings ``true/false``, ``1/0``, ``yes/no``, ``on/off``.

        Raises:
            ConfigurationError: If missing without default or not a boolean.
        """
        raw = self._raw(key, default)
        if raw is default:
            return default
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, str):
            lowered = raw.strip().lower()
            if lowered in _TRUE:
                return True
            if lowered in _FALSE:
                return False
        raise ConfigurationError("expected a boolean", key=self.key_path(key))

    @overload
    def get_path(self, key: str) -> Path: ...
    @overload
    def get_path[D](self, key: str, default: D) -> Path | D: ...
    def get_path(self, key: str, default: object = _MISSING) -> object:
        """Return a filesystem path (``~`` is expanded).

        Raises:
            ConfigurationError: If missing without default or not a non-empty string.
        """
        raw = self._raw(key, default)
        if raw is default:
            return default
        if not isinstance(raw, str) or not raw.strip():
            raise ConfigurationError("expected a non-empty path", key=self.key_path(key))
        return Path(raw).expanduser()

    @overload
    def get_choice(self, key: str, choices: Collection[str]) -> str: ...
    @overload
    def get_choice[D](self, key: str, choices: Collection[str], default: D) -> str | D: ...
    def get_choice(self, key: str, choices: Collection[str], default: object = _MISSING) -> object:
        """Return a string restricted to ``choices``.

        Raises:
            ConfigurationError: If missing without default or not one of ``choices``.
        """
        raw = self._raw(key, default)
        if raw is default:
            return default
        if not isinstance(raw, str) or raw not in choices:
            expected = ", ".join(sorted(choices))
            raise ConfigurationError(f"expected one of: {expected}", key=self.key_path(key))
        return raw

    @overload
    def get_secret_ref(self, key: str) -> SecretRef: ...
    @overload
    def get_secret_ref[D](self, key: str, default: D) -> SecretRef | D: ...
    def get_secret_ref(self, key: str, default: object = _MISSING) -> object:
        """Return a secret reference such as ``env:DB_PASSWORD``.

        Literal secrets are rejected, and the error never echoes the value.

        Raises:
            ConfigurationError: If missing without default or not a reference.
        """
        raw = self._raw(key, default)
        if raw is default:
            return default
        if not isinstance(raw, str):
            raise ConfigurationError("expected a secret reference", key=self.key_path(key))
        try:
            return SecretRef.parse(raw)
        except ValueError as exc:
            raise ConfigurationError(str(exc), key=self.key_path(key)) from None

    def _raw(self, key: str, default: object) -> object:
        if key in self._data:
            return self._data[key]
        if default is _MISSING:
            raise ConfigurationError("required key is missing", key=self.key_path(key))
        return default

    def _check_range(
        self, key: str, value: float, minimum: float | None, maximum: float | None
    ) -> None:
        if minimum is not None and value < minimum:
            raise ConfigurationError(f"must be >= {minimum}", key=self.key_path(key))
        if maximum is not None and value > maximum:
            raise ConfigurationError(f"must be <= {maximum}", key=self.key_path(key))


@dataclass(frozen=True, slots=True)
class RuntimeSettings:
    """Validated settings of the ``[runtime]`` table.

    Attributes:
        name: Name of the Runtime, used in logs, events and metric tags.
        timeout: Default execution timeout in seconds, or ``None`` for none.
        workspace: Whether each execution gets a private temporary directory.
        workspace_root: Parent directory of workspaces (system default if ``None``).
        keep_workspace: Keep the workspace after the execution, for debugging.
    """

    name: str = "orchestrator"
    timeout: float | None = None
    workspace: bool = False
    workspace_root: Path | None = None
    keep_workspace: bool = False

    @classmethod
    def from_section(cls, section: ConfigSection) -> RuntimeSettings:
        """Validate the ``[runtime]`` table.

        Raises:
            ConfigurationError: If a key is unknown or invalid.
        """
        section.check_keys(("name", "timeout", "workspace", "workspace_root", "keep_workspace"))
        name = section.get_str("name", "orchestrator")
        if not _RUNTIME_NAME_RE.match(name):
            msg = "must have 1-64 characters: letters, digits, '.', '_' or '-'"
            raise ConfigurationError(msg, key=section.key_path("name"))
        timeout = section.get_float("timeout", None)
        if timeout is not None and timeout <= 0:
            raise ConfigurationError("must be greater than zero", key=section.key_path("timeout"))
        return cls(
            name=name,
            timeout=timeout,
            workspace=section.get_bool("workspace", False),
            workspace_root=section.get_path("workspace_root", None),
            keep_workspace=section.get_bool("keep_workspace", False),
        )


class Configuration:
    """Merged, validated and immutable configuration of a Runtime.

    Example:
        >>> config = Configuration.from_mapping({"runtime": {"timeout": 30}, "app": {"x": 1}})
        >>> config.runtime.timeout
        30.0
        >>> config.section("app").get_int("x")
        1
    """

    __slots__ = ("_root", "_runtime")

    def __init__(self, root: ConfigSection) -> None:
        """Validate ``root``. Prefer :meth:`load` or :meth:`from_mapping`.

        Raises:
            ConfigurationError: If the reserved tables are invalid.
        """
        self._root = root
        self._runtime = RuntimeSettings.from_section(root.section("runtime"))
        capabilities = root.section("capabilities")
        for name in capabilities:
            capabilities.section(name)

    @classmethod
    def from_mapping(cls, data: Mapping[str, object]) -> Configuration:
        """Create a configuration from an in-memory mapping."""
        return cls(ConfigSection(data))

    @classmethod
    def load(
        cls,
        *,
        file: str | os.PathLike[str] | None = None,
        environ: Mapping[str, str] | None = None,
        env_prefix: str | None = None,
        overrides: Sequence[Mapping[str, object]] = (),
    ) -> Configuration:
        """Load and merge every source, from lowest to highest precedence.

        Args:
            file: TOML file, if any.
            environ: Environment variables, read only if ``env_prefix`` is set.
            env_prefix: Prefix of the variables to read, such as ``ORCHESTRATOR``.
            overrides: Explicit settings, applied in order, with highest precedence.

        Raises:
            ConfigurationError: If a source is unreadable or the result is invalid.
        """
        merged: dict[str, object] = {}
        if file is not None:
            merged = _merge(merged, read_toml(Path(file)), "")
        if env_prefix:
            merged = _merge(merged, environment_tree(environ or {}, env_prefix), "")
        for override in overrides:
            merged = _merge(merged, override, "")
        return cls(ConfigSection(merged))

    @property
    def runtime(self) -> RuntimeSettings:
        """Validated ``[runtime]`` settings."""
        return self._runtime

    @property
    def root(self) -> ConfigSection:
        """The whole configuration tree."""
        return self._root

    def section(self, path: str) -> ConfigSection:
        """Return the table at dotted ``path`` (empty if absent), e.g. ``"app"``.

        Raises:
            ConfigurationError: If an element of the path is not a table.
        """
        section = self._root
        for key in path.split("."):
            section = section.section(key)
        return section

    def capability(self, name: str) -> ConfigSection:
        """Return the ``[capabilities.<name>]`` table (empty if absent)."""
        return self._root.section("capabilities").section(name)

    def __repr__(self) -> str:
        """Return the top-level table names; values are omitted."""
        return f"Configuration(sections={sorted(self._root)!r})"


def read_toml(path: Path) -> dict[str, object]:
    """Read a TOML configuration file.

    Raises:
        ConfigurationError: If the file is missing, unreadable or invalid.
    """
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except FileNotFoundError:
        msg = f"configuration file not found: {path}"
        raise ConfigurationError(msg) from None
    except OSError as exc:
        msg = f"cannot read configuration file {path}: {exc.strerror}"
        raise ConfigurationError(msg) from None
    except tomllib.TOMLDecodeError as exc:
        msg = f"invalid TOML in {path}: {exc}"
        raise ConfigurationError(msg) from None


def environment_tree(environ: Mapping[str, str], prefix: str) -> dict[str, object]:
    """Convert ``<PREFIX>_<A>__<B>=value`` variables into ``{"a": {"b": "value"}}``.

    Variables without ``__`` after the prefix are ignored.

    Raises:
        ConfigurationError: If a variable name has an empty or invalid segment.
    """
    head = prefix.upper().rstrip("_") + "_"
    tree: dict[str, object] = {}
    for name in sorted(environ):
        if not name.upper().startswith(head):
            continue
        rest = name[len(head) :]
        if "__" not in rest:
            continue
        segments = rest.lower().split("__")
        if not all(_ENV_SEGMENT_RE.match(segment) for segment in segments):
            msg = f"invalid configuration variable name {name!r}"
            raise ConfigurationError(msg)
        branch: dict[str, object] = {}
        node = branch
        for segment in segments[:-1]:
            child: dict[str, object] = {}
            node[segment] = child
            node = child
        node[segments[-1]] = environ[name]
        tree = _merge(tree, branch, "")
    return tree


def _merge(
    base: Mapping[str, object], override: Mapping[str, object], path: str
) -> dict[str, object]:
    result = dict(base)
    for key, value in override.items():
        current = result.get(key)
        key_path = _join(path, key)
        if isinstance(value, Mapping):
            if current is None:
                current = {}
            if not isinstance(current, Mapping):
                raise ConfigurationError("a value and a table were both given", key=key_path)
            result[key] = _merge(current, value, key_path)
        else:
            if isinstance(current, Mapping):
                raise ConfigurationError("a table and a value were both given", key=key_path)
            result[key] = value
    return result
