from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .spec import ExecutionSpecification


class ConfigLoader:
    """Loads execution specs from JSON or YAML-like configuration files."""

    def load_spec(self, file_path: str) -> ExecutionSpecification:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(file_path)

        content = path.read_text(encoding="utf-8")
        data: dict[str, Any]
        if path.suffix.lower() == ".json":
            data = json.loads(content)
        else:
            try:
                import yaml  # type: ignore
            except ModuleNotFoundError as exc:
                raise ValueError("YAML support requires the PyYAML package") from exc
            data = yaml.safe_load(content)

        if not isinstance(data, dict):
            raise ValueError("Specification content must be a mapping")

        return ExecutionSpecification.from_mapping(data)
