"""SqlCapability: registers SQL access in the Runtime and opens one session per execution."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any, ClassVar, Self

from orchestrator_core import Capability, CapabilityError, ConfigSection, ExecutionContext
from orchestrator_sql._provider import SqlProvider
from orchestrator_sql._session import SqlSession

_logger = logging.getLogger("orchestrator_sql")


class SqlCapability(Capability[SqlSession]):
    """SQL Capability. The engine-specific work is delegated to a :class:`SqlProvider`.

    Configuration (``[capabilities.sql]``)::

        provider = "sqlite"  # key of the providers mapping given to the builder
        database = "data/app.db"  # every other key belongs to the Provider

    Example::

        runtime = (
            RuntimeBuilder()
            .with_config_file("orchestrator.toml")
            .with_capability(SqlCapability, providers={"sqlite": SqliteProvider})
            .build()
        )


        def automation(ctx: ExecutionContext) -> int:
            sql = ctx.capability(SqlCapability)
            return sql.scalar("SELECT count(*) FROM orders WHERE region = :region", {"region": "S"})
    """

    default_name: ClassVar[str] = "sql"
    core_api: ClassVar[str | None] = "0.1"

    def __init__(self, provider: SqlProvider) -> None:
        """Create the Capability around ``provider``."""
        self._provider = provider

    @property
    def provider(self) -> SqlProvider:
        """The Provider in use."""
        return self._provider

    @classmethod
    def from_config(
        cls,
        section: ConfigSection,
        /,
        *,
        providers: Mapping[str, type[SqlProvider]] | None = None,
        **options: Any,  # noqa: ANN401 - mirrors Capability.from_config
    ) -> Self:
        """Choose the Provider named by ``provider`` and build it from the rest of the table.

        Args:
            section: The ``[capabilities.<name>]`` table.
            providers: Provider classes allowed for this Runtime, by name. Only
                these can be selected by configuration. Required.
            **options: Not accepted; present for signature compatibility.

        Raises:
            CapabilityError: If ``providers`` is missing or unknown options are given.
            ConfigurationError: If ``provider`` is missing or not allowed, or the
                Provider settings are invalid.
        """
        if providers is None or options:
            msg = "SqlCapability.from_config accepts exactly one option: providers={name: class}"
            raise CapabilityError(msg)
        name = section.get_choice("provider", providers.keys())
        provider_settings = ConfigSection(
            {key: value for key, value in section.items() if key != "provider"},
            section.path,
        )
        return cls(providers[name].from_config(provider_settings))

    def verify(self) -> None:
        """Delegate to the Provider."""
        self._provider.verify()

    def open(self, ctx: ExecutionContext) -> SqlSession:
        """Connect and return the session of this execution.

        The connection is closed in ``finalize``; a transaction left open by the
        automation is rolled back first.
        """
        session = SqlSession(self._provider, self._provider.connect())
        ctx.resources.callback(session.close)
        ctx.add_finalizer(session.finalize)
        _logger.debug("SQL session opened: %s", self._provider.describe())
        return session
