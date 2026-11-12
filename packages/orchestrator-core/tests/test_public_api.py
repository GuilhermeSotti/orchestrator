"""The public surface is exactly the one approved in RFC-0002, and the Core stays stdlib-only."""

from __future__ import annotations

import ast
import importlib
import inspect
import re
import sys
from pathlib import Path
from typing import TypeAliasType

import orchestrator_core

SRC = Path(orchestrator_core.__file__).parent

APPROVED = {
    "CORE_API_VERSION", "Automation", "CancellationToken", "Capability", "CapabilityError",
    "CapabilityNotFoundError", "CapabilityUnavailableError", "Clock", "ConfigSection",
    "Configuration", "ConfigurationError", "DuplicateCapabilityError", "ErrorInfo", "Event",
    "EventHandler", "ExecutionCancelledError", "ExecutionContext", "ExecutionFailedError",
    "ExecutionFinished", "ExecutionInterruptedError", "ExecutionOutcome", "ExecutionRecord",
    "ExecutionRecordSink", "ExecutionResult", "ExecutionStarted", "ExecutionStatus",
    "ExecutionTimeoutError", "Finalizer", "FunctionStage", "IncompatibleCapabilityError",
    "MetricsRecorder", "OrchestratorError", "Phase", "PipelineDefinitionError", "ProviderError",
    "ResourceScope", "RetryAttempt", "RetryPolicy", "Runtime", "RuntimeBuilder",
    "RuntimeSettings", "Secret", "SecretRef", "SecretResolutionError", "SecretResolver",
    "SecretStore", "Stage", "StageFinished", "StageOutcome", "StageRecord", "StageStarted",
    "StageStatus", "__version__", "is_retryable", "retry",
}  # fmt: skip

PUBLIC_SUBMODULES = {
    "orchestrator_core.logs": {
        "TEXT_FORMAT", "ExecutionContextFilter", "JsonFormatter", "RedactingFilter",
        "configure_logging",
    },
    "orchestrator_core.testing": {
        "EventRecorder", "FakeClock", "InMemoryMetrics", "InMemoryRecordSink",
        "check_capability_conformance",
    },
}  # fmt: skip


def test_exported_names_are_exactly_the_approved_ones() -> None:
    assert set(orchestrator_core.__all__) == APPROVED
    assert len(orchestrator_core.__all__) == len(APPROVED)
    for name in APPROVED:
        assert hasattr(orchestrator_core, name), name


def test_public_submodules_export_the_approved_names() -> None:
    for module_name, names in PUBLIC_SUBMODULES.items():
        module = importlib.import_module(module_name)
        assert set(module.__all__) == names


def test_every_public_object_is_documented() -> None:
    undocumented = []
    objects = [(name, getattr(orchestrator_core, name)) for name in APPROVED]
    for module_name, names in PUBLIC_SUBMODULES.items():
        module = importlib.import_module(module_name)
        objects.extend((f"{module_name}.{n}", getattr(module, n)) for n in names)
    for name, obj in objects:
        if isinstance(obj, str | TypeAliasType):
            continue
        if not inspect.getdoc(obj):
            undocumented.append(name)
        if inspect.isclass(obj):
            for member_name, member in vars(obj).items():
                if member_name.startswith("_") or not callable(member):
                    continue
                if not inspect.getdoc(member):
                    undocumented.append(f"{name}.{member_name}")
    assert undocumented == []


def test_version_is_semver_and_api_version_is_major_minor() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+", orchestrator_core.__version__)
    assert re.fullmatch(r"\d+\.\d+", orchestrator_core.CORE_API_VERSION)
    assert orchestrator_core.__version__.startswith(orchestrator_core.CORE_API_VERSION + ".")


def test_core_imports_only_the_standard_library() -> None:
    """D-04 / ADR-0005: the Core has no third-party runtime dependency."""
    offenders = []
    for path in SRC.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                roots = [node.module.split(".")[0]]
            else:
                continue
            offenders.extend(
                f"{path.name}: {root}"
                for root in roots
                if root != "orchestrator_core" and root not in sys.stdlib_module_names
            )
    assert offenders == []


def test_internal_modules_are_private() -> None:
    public = {"__init__.py", "logs.py", "testing.py"}
    for path in SRC.glob("*.py"):
        assert path.name in public or path.name.startswith("_"), path.name


def test_package_is_typed() -> None:
    assert (SRC / "py.typed").exists()
