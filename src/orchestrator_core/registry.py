from __future__ import annotations

from importlib import metadata
from typing import Any


class CapabilityRegistry:
    """Registry for discovered capability providers and their stages."""

    def __init__(self) -> None:
        self._providers: dict[str, Any] = {}
        self._capabilities: list[Any] = []

    def register(self, name: str, provider: Any) -> None:
        self._providers[name] = provider
        if provider not in self._capabilities:
            self._capabilities.append(provider)

    def resolve(self, name: str) -> Any | None:
        return self._providers.get(name)

    def list_capabilities(self) -> list[Any]:
        return list(self._capabilities)

    def get_stages_for(self, spec: Any) -> list[Any]:
        stages: list[Any] = []
        for capability in self._capabilities:
            if hasattr(capability, "is_applicable") and not capability.is_applicable(spec):
                continue
            if hasattr(capability, "provide_stages"):
                stages.extend(capability.provide_stages(spec))
        return stages

    def discover(self, group: str = "orchestrator.capabilities") -> None:
        try:
            entries = metadata.entry_points(group=group)
        except TypeError:
            entries = metadata.entry_points().get(group, [])

        for entry_point in entries:
            provider = entry_point.load()
            if callable(provider):
                provider = provider()
            self.register(entry_point.name, provider)
