from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ExecutionSpecification:
    """Immutable execution contract loaded from configuration sources."""

    name: str
    tasks: list[str]
    parameters: dict[str, Any] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    runner: dict[str, Any] = field(default_factory=dict)
    environment: dict[str, str] = field(default_factory=dict)
    timeout: int | None = None
    retries: int = 0
    strict: bool = False

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "ExecutionSpecification":
        if not isinstance(data, dict):
            raise ValueError("ExecutionSpecification expects a dictionary payload")

        name = data.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("ExecutionSpecification requires a non-empty 'name'")

        raw_tasks = data.get("tasks")
        if not isinstance(raw_tasks, list) or not raw_tasks:
            raise ValueError("ExecutionSpecification requires a non-empty 'tasks' list")
        tasks = [str(task) for task in raw_tasks]

        parameters = data.get("parameters", {})
        if not isinstance(parameters, dict):
            raise ValueError("'parameters' must be a mapping")
        
        runner = data.get("runner", {})
        if not isinstance(runner, dict):    
            raise ValueError("'runner' must be a mapping")
        

        dependencies = data.get("dependencies", [])
        if not isinstance(dependencies, list):
            raise ValueError("'dependencies' must be a list")

        environment = data.get("environment", {})
        if not isinstance(environment, dict):
            raise ValueError("'environment' must be a mapping")

        return cls(
            name=name,
            tasks=tasks,
            parameters=dict(parameters),
            runner=dict(runner),
            dependencies=[str(dep) for dep in dependencies],
            environment={str(key): str(value) for key, value in environment.items()},
            timeout=data.get("timeout"),
            retries=int(data.get("retries", 0)),
            strict=bool(data.get("strict", False)),
        )
