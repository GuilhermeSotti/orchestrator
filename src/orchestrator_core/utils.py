from __future__ import annotations

from typing import Any


def ensure_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("Expected a mapping")
    return value


def normalize_name(name: str) -> str:
    return name.strip().lower().replace(" ", "-")
