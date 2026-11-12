from __future__ import annotations

from typing import Any

from ..context import ExecutionContext
from ..spec import ExecutionSpecification


class InMemoryConfigurationPort:
    def load_spec(self, file_path: str) -> ExecutionSpecification:
        raise NotImplementedError("Use the concrete loader for real files")


class InMemoryStoragePort:
    def __init__(self) -> None:
        self.results: list[ExecutionContext] = []

    def save_result(self, context: ExecutionContext) -> None:
        self.results.append(context)


class InMemoryInfrastructurePort:
    def setup_environment(self, spec: ExecutionSpecification) -> dict[str, Any]:
        return {"name": spec.name, "tasks": list(spec.tasks)}


class InMemoryNotificationPort:
    def __init__(self) -> None:
        self.notifications: list[tuple[str, ExecutionContext]] = []

    def notify(self, status: str, context: ExecutionContext) -> None:
        self.notifications.append((status, context))


class InMemorySecretsPort:
    def __init__(self) -> None:
        self.secrets: dict[str, str] = {}

    def get_secret(self, key: str) -> str | None:
        return self.secrets.get(key)


class InMemoryArtifactPort:
    def __init__(self) -> None:
        self.artifacts: dict[str, Any] = {}

    def save_artifact(self, name: str, data: Any) -> None:
        self.artifacts[name] = data


class InMemoryEventPort:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    def publish(self, event_name: str, payload: dict[str, Any]) -> None:
        self.events.append((event_name, payload))


class InMemoryMetricsPort:
    def __init__(self) -> None:
        self.metrics: dict[str, float] = {}

    def record(self, metric_name: str, value: float) -> None:
        self.metrics[metric_name] = value


class InMemoryCachePort:
    def __init__(self) -> None:
        self.values: dict[str, Any] = {}

    def get(self, key: str) -> Any:
        return self.values.get(key)

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        self.values[key] = value
