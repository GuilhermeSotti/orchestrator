"""Import boundaries between the incubated packages (ADR-0001, ADR-0004, ADR-0015).

Each package may import only the standard library, itself and its declared
platform dependencies. Tests follow the same rule (plus pytest).
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

ALLOWED = {
    "packages/orchestrator-core": {"orchestrator_core"},
    "examples/hello-automation": {"orchestrator_core", "hello_automation"},
}
TEST_ONLY = {"pytest"}


def imported_roots(path: Path) -> set[str]:
    """Return the top-level modules imported by ``path`` (absolute imports only)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
    return roots


@pytest.mark.parametrize("project", sorted(ALLOWED))
def test_projects_import_only_what_they_declare(project: str) -> None:
    base = ROOT / project
    violations: list[str] = []
    for path in sorted(base.rglob("*.py")):
        relative = path.relative_to(base)
        allowed = ALLOWED[project] | (TEST_ONLY if relative.parts[0] == "tests" else set())
        violations.extend(
            f"{relative}: {root}"
            for root in sorted(imported_roots(path))
            if root not in allowed and root not in sys.stdlib_module_names
        )
    assert violations == []


def test_every_package_folder_is_covered() -> None:
    folders = {
        str(path.relative_to(ROOT)).replace("\\", "/")
        for group in ("packages", "examples")
        for path in (ROOT / group).iterdir()
        if (path / "pyproject.toml").is_file()
    }
    assert folders == set(ALLOWED)


def test_package_dependencies_match_the_boundaries() -> None:
    import tomllib

    expected: dict[str, set[str]] = {
        "packages/orchestrator-core": set(),
    }
    for project, dependencies in expected.items():
        data = tomllib.loads((ROOT / project / "pyproject.toml").read_text(encoding="utf-8"))
        declared = {
            requirement.split(">")[0].split("<")[0].split("=")[0].strip()
            for requirement in data["project"]["dependencies"]
        }
        assert declared == dependencies, project
