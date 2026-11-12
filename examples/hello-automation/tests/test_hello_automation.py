from __future__ import annotations

import json
from pathlib import Path

import pytest

from hello_automation import Parameters, summarize_texts
from hello_automation.__main__ import main
from orchestrator_core import RuntimeBuilder, StageStatus

DATA = Path(__file__).resolve().parents[1] / "data"
CONFIG = Path(__file__).resolve().parents[1] / "orchestrator.toml"


def test_automation_through_the_public_api(tmp_path: Path) -> None:
    runtime = (
        RuntimeBuilder()
        .with_environment({}, prefix=None)
        .with_config_file(CONFIG)
        .with_settings({"runtime": {"workspace_root": str(tmp_path)}})
        .build()
    )
    output = tmp_path / "out" / "summary.json"
    result = runtime.run(
        summarize_texts,
        parameters={"input_dir": str(DATA), "output_file": str(output)},
        parameters_validator=Parameters.validate,
    )
    result.raise_for_status()
    assert result.output == {"files": 2, "lines": 3, "words": 28}
    assert json.loads(output.read_text(encoding="utf-8")) == result.output
    assert list(tmp_path.glob("orchestrator-*")) == []  # workspace removed by finalize


def test_invalid_parameters_stop_before_the_automation(tmp_path: Path) -> None:
    runtime = RuntimeBuilder().with_environment({}, prefix=None).with_config_file(CONFIG).build()
    result = runtime.run(
        summarize_texts,
        parameters={"input_dir": str(tmp_path / "absent"), "output_file": "x.json"},
        parameters_validator=Parameters.validate,
    )
    assert result.stage("prepare_execution").status is StageStatus.FAILED
    assert result.stage("execute_automation").status is StageStatus.SKIPPED
    assert "input folder not found" in str(result.error)


def test_command_line(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    output = tmp_path / "summary.json"
    assert main([str(DATA), "--output", str(output), "--config", str(CONFIG)]) == 0
    record = json.loads(capsys.readouterr().out)
    assert record["status"] == "succeeded"
    assert record["runtime"] == "hello-automation"
    assert json.loads(output.read_text(encoding="utf-8"))["files"] == 2
    assert main([str(tmp_path / "absent"), "--output", str(output)]) == 1
