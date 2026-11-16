"""NotificationCapability: registers channels in the Runtime and opens a Notifier per execution."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from types import MappingProxyType
from typing import Any, ClassVar, Self

from orchestrator_core import (
    Capability,
    CapabilityError,
    ConfigSection,
    ConfigurationError,
    ExecutionContext,
)
from orchestrator_notifications._channel import NotificationChannel
from orchestrator_notifications._model import NOTIFY_OUTCOME, NOTIFY_STARTED, STATUSES
from orchestrator_notifications._notifier import ChannelSettings, Formatter, Notifier
from orchestrator_notifications._texts import default_formatter

_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_POLICY_KEYS = ("provider", "required", "attempts", "delay")
_PROVISION = "provision_dependencies"


class NotificationCapability(Capability[Notifier]):
    """Notifications to people through channels such as e-mail and Microsoft Teams.

    Nothing is sent without explicit configuration: a channel is used only when
    named by the automation, by ``default_channels`` or by the lifecycle table,
    and lifecycle notices also need the stages :class:`NotifyStarted` and
    :class:`NotifyOutcome` (RFC-0007, section 3). A failing channel does not
    change the outcome unless it is ``required``.

    Configuration (``[capabilities.notifications]``)::

        default_channels = ["operacao"]

        [capabilities.notifications.lifecycle]  # absent: no lifecycle notice
        failed = ["operacao"]

        [capabilities.notifications.channels.operacao]
        provider = "smtp"  # key of the providers mapping given to the builder
        required = false  # policy keys: required, attempts, delay
        host = "smtp.exemplo.interno"  # every other key belongs to the Provider

    Example::

        runtime = (
            RuntimeBuilder()
            .with_config_file("orchestrator.toml")
            .with_capability(NotificationCapability, providers={"smtp": SmtpChannel})
            .with_stage(NotifyOutcome(), after="finalize")
            .build()
        )

    Register it before the other Capabilities: they are opened in order, and a
    notice can only be sent if this Capability was opened.
    """

    default_name: ClassVar[str] = "notifications"
    core_api: ClassVar[str | None] = "0.2"

    def __init__(
        self,
        channels: Mapping[str, NotificationChannel | ChannelSettings],
        *,
        default_channels: Sequence[str] = (),
        lifecycle: Mapping[str, Sequence[str]] | None = None,
        formatter: Formatter | None = None,
    ) -> None:
        """Create the Capability.

        Args:
            channels: Channels by name, as Providers or with their policy.
            default_channels: Channels used by ``send()`` without ``channel``.
            lifecycle: Channels notified for each status (``started``,
                ``succeeded``, ``failed``, ``cancelled``, ``timed_out``).
            formatter: Builds lifecycle notifications; default: formal PT-BR.

        Raises:
            ValueError: If a name is invalid or refers to an unknown channel.
        """
        settings: dict[str, ChannelSettings] = {}
        for name, value in channels.items():
            if not _NAME_RE.match(name):
                msg = f"invalid channel name {name!r}"
                raise ValueError(msg)
            settings[name] = value if isinstance(value, ChannelSettings) else ChannelSettings(value)
        self._channels = MappingProxyType(settings)
        self._default = _known(tuple(default_channels), settings, "default_channels")
        cycle: dict[str, tuple[str, ...]] = {}
        for status, names in (lifecycle or {}).items():
            if status not in STATUSES:
                msg = f"unknown lifecycle status {status!r}; expected one of {', '.join(STATUSES)}"
                raise ValueError(msg)
            known = _known(tuple(names), settings, f"lifecycle.{status}")
            if known:
                cycle[status] = known
        self._lifecycle = MappingProxyType(cycle)
        self._formatter = formatter or default_formatter

    @property
    def channels(self) -> Mapping[str, NotificationChannel]:
        """Channel Providers by name."""
        return MappingProxyType({name: item.provider for name, item in self._channels.items()})

    @property
    def lifecycle(self) -> Mapping[str, tuple[str, ...]]:
        """Channels notified for each lifecycle status."""
        return self._lifecycle

    @classmethod
    def from_config(
        cls,
        section: ConfigSection,
        /,
        *,
        providers: Mapping[str, type[NotificationChannel]] | None = None,
        formatter: Formatter | None = None,
        **options: Any,  # noqa: ANN401 - mirrors Capability.from_config
    ) -> Self:
        """Build the channels allowed by ``providers`` from the configuration table.

        Args:
            section: The ``[capabilities.<name>]`` table.
            providers: Channel classes allowed for this Runtime, by name. Only
                these can be selected by configuration. Required.
            formatter: Optional builder of lifecycle notifications.
            **options: Not accepted; present for signature compatibility.

        Raises:
            CapabilityError: If ``providers`` is missing or unknown options are given.
            ConfigurationError: If the table has unknown or invalid keys.
        """
        if providers is None or options:
            msg = (
                "NotificationCapability.from_config accepts providers={name: class} "
                "and, optionally, formatter="
            )
            raise CapabilityError(msg)
        section.check_keys(("default_channels", "lifecycle", "channels"))
        table = section.section("channels")
        channels: dict[str, ChannelSettings] = {}
        for name in table:
            item = table.section(name)
            kind = item.get_choice("provider", providers.keys())
            provider = providers[kind].from_config(
                ConfigSection(
                    {key: value for key, value in item.items() if key not in _POLICY_KEYS},
                    item.path,
                )
            )
            channels[name] = ChannelSettings(
                provider,
                required=item.get_bool("required", False),
                attempts=item.get_int("attempts", 1, minimum=1),
                delay=item.get_float("delay", 0.0, minimum=0.0),
            )
        cycle_table = section.section("lifecycle")
        cycle_table.check_keys(STATUSES)
        try:
            return cls(
                channels,
                default_channels=_strings(section, "default_channels"),
                lifecycle={status: _strings(cycle_table, status) for status in cycle_table},
                formatter=formatter,
            )
        except ValueError as exc:
            raise ConfigurationError(str(exc), key=section.path) from None

    def verify(self) -> None:
        """Verify every channel."""
        for settings in self._channels.values():
            settings.provider.verify()

    def open(self, ctx: ExecutionContext) -> Notifier:
        """Return the Notifier of this execution.

        Raises:
            ConfigurationError: If lifecycle notices are configured but the
                pipeline lacks their stages (RFC-0007, answer 6). The automation
                does not start.
        """
        self._check_stages(ctx.stages)
        return Notifier(ctx, self._channels, self._default, self._lifecycle, self._formatter)

    def _check_stages(self, stages: tuple[str, ...]) -> None:
        needed = []
        if "started" in self._lifecycle:
            needed.append(NOTIFY_STARTED)
        if any(status != "started" for status in self._lifecycle):
            needed.append(NOTIFY_OUTCOME)
        missing = [name for name in needed if name not in stages]
        if missing:
            msg = (
                f"lifecycle notifications are configured but the pipeline has no stage "
                f"{', '.join(missing)}; install NotifyStarted and NotifyOutcome with "
                f"RuntimeBuilder.with_stage"
            )
            raise ConfigurationError(msg, key="lifecycle")
        if (
            NOTIFY_STARTED in needed
            and _PROVISION in stages
            and stages.index(NOTIFY_STARTED) < stages.index(_PROVISION)
        ):
            msg = f"stage {NOTIFY_STARTED} must run after {_PROVISION}"
            raise ConfigurationError(msg, key="lifecycle")


def _known(names: tuple[str, ...], channels: Mapping[str, object], where: str) -> tuple[str, ...]:
    for name in names:
        if name not in channels:
            msg = f"{where} refers to unknown channel {name!r}"
            raise ValueError(msg)
    return names


def _strings(section: ConfigSection, key: str) -> tuple[str, ...]:
    if key not in section:
        return ()
    value = section[key]
    if not isinstance(value, (list, tuple)) or not all(isinstance(item, str) for item in value):
        raise ConfigurationError("expected a list of channel names", key=section.key_path(key))
    return tuple(value)
