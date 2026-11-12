from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from .spec import ExecutionSpecification


@dataclass
class ExecutionContext:
    """Mutable runtime context passed through pipeline stages."""

    spec: ExecutionSpecification
    status: str = "pending"
    environment: dict[str, str] = field(default_factory=dict)
    variables: dict[str, Any] = field(default_factory=dict)
    logs: list[str] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, float] = field(default_factory=dict)
    execution_id: str = field(default_factory=lambda: uuid4().hex)
    correlation_id: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None

    @classmethod
    def from_spec(cls, spec: ExecutionSpecification) -> "ExecutionContext":
        return cls(spec=spec, environment=dict(spec.environment))

    def add_log(self, message: str) -> None:
        self.logs.append(message)

    def set_status(self, status: str) -> None:
        self.status = status

    def set_variable(self, name: str, value: Any) -> None:
        self.variables[name] = value

    def add_metric(self, name: str, value: float) -> None:
        self.metrics[name] = value

    def add_artifact(self, name: str, value: Any) -> None:
        self.artifacts[name] = value

    def set_correlation_id(self, correlation_id: str) -> None:
        self.correlation_id = correlation_id

    def mark_started(self) -> None:
        self.started_at = datetime.now(timezone.utc)

    def mark_finished(self) -> None:
        self.finished_at = datetime.now(timezone.utc)
