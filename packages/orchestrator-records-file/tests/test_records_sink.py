from __future__ import annotations

import json
import logging
import os
import threading
from datetime import UTC, date
from pathlib import Path

import pytest

from orchestrator_core import ExecutionContext, ExecutionRecord, ExecutionStatus, RuntimeBuilder
from orchestrator_core.testing import InMemoryMetrics
from orchestrator_records_file import JsonLinesRecordSink

SENTINEL = "S3NT1NEL-records-5d1e"


class _Sentinel:
    def resolve(self, target: str) -> str:
        return f"{SENTINEL}-{target}"


def _builder(sink: JsonLinesRecordSink) -> RuntimeBuilder:
    return (
        RuntimeBuilder()
        .with_environment({}, prefix=None)
        .with_secret_resolver("test", _Sentinel())
        .with_record_sink(sink)
    )


def _lines(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _record(tmp_path: Path) -> ExecutionRecord:
    folder = tmp_path / "seed"
    folder.mkdir()
    return _builder(JsonLinesRecordSink(folder)).build().run(lambda ctx: None).record


def test_each_execution_becomes_one_json_line(tmp_path: Path) -> None:
    sink = JsonLinesRecordSink(tmp_path, prefix="vendas")
    runtime = _builder(sink).build()
    results = [runtime.run(lambda ctx: None) for _ in range(3)]
    day = results[0].record.finished_at.astimezone(UTC).date()
    path = sink.path_for(day)
    assert path.name.startswith(f"vendas-{day:%Y-%m-%d}-")
    assert path.name.endswith(f"-{os.getpid()}.jsonl")
    lines = _lines(path)
    assert [line["execution_id"] for line in lines] == [r.execution_id for r in results]
    expected = results[0].record.to_dict()  # final record; sinks get it at persist_logs
    assert set(lines[0]) == set(expected)
    for key in ("execution_id", "automation", "runtime", "status", "started_at", "error"):
        assert lines[0][key] == expected[key]
    assert all("output" not in line and "parameters" not in line for line in lines)
    assert sink.folder == tmp_path.absolute()


def test_single_writer_name_without_host_and_process(tmp_path: Path) -> None:
    sink = JsonLinesRecordSink(tmp_path, prefix="unico", per_process=False)
    assert sink.path_for(date(2026, 11, 15)).name == "unico-2026-11-15.jsonl"


def test_eight_threads_never_lose_or_mix_lines(tmp_path: Path) -> None:
    record = _record(tmp_path)
    sink = JsonLinesRecordSink(tmp_path)
    barrier = threading.Barrier(8)

    def worker() -> None:
        barrier.wait()
        for _ in range(50):
            sink.write(record)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    lines = _lines(sink.path_for(record.finished_at.astimezone(UTC).date()))
    assert len(lines) == 400
    assert {line["execution_id"] for line in lines} == {record.execution_id}


def test_write_failure_never_changes_the_status(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    folder = tmp_path / "records"
    folder.mkdir()
    sink = JsonLinesRecordSink(folder)
    folder.rmdir()  # simulates a lost share or a folder without permission
    metrics = InMemoryMetrics()
    with caplog.at_level(logging.WARNING):
        result = _builder(sink).with_metrics(metrics).build().run(lambda ctx: "ok")
    assert result.status is ExecutionStatus.SUCCEEDED
    assert result.output == "ok"
    assert metrics.counter("orchestrator.record_sink.errors", sink="JsonLinesRecordSink") == 1
    assert "JsonLinesRecordSink failed" in caplog.text


class _FullDisk:
    def open(self, *args: object) -> object:
        raise OSError(28, "No space left on device")


def test_disk_full_never_changes_the_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sink = JsonLinesRecordSink(tmp_path)
    monkeypatch.setattr(sink, "path_for", lambda day: _FullDisk())
    metrics = InMemoryMetrics()
    result = _builder(sink).with_metrics(metrics).build().run(lambda ctx: "ok")
    assert result.status is ExecutionStatus.SUCCEEDED
    assert metrics.counter("orchestrator.record_sink.errors", sink="JsonLinesRecordSink") == 1
    with pytest.raises(OSError, match="No space"):
        sink.write(result.record)


def test_secret_values_never_reach_the_file(tmp_path: Path) -> None:
    sink = JsonLinesRecordSink(tmp_path)

    def automation(ctx: ExecutionContext) -> None:
        value = ctx.secrets.resolve("test:database").reveal()
        msg = f"login refused for {value}"
        raise RuntimeError(msg)

    result = _builder(sink).build().run(automation)
    assert result.status is ExecutionStatus.FAILED
    text = sink.path_for(result.record.finished_at.astimezone(UTC).date()).read_text("utf-8")
    assert SENTINEL not in text
    assert "login refused for" in text


def test_retention_removes_only_this_sinks_old_files(tmp_path: Path) -> None:
    names = {
        "vendas-2026-01-10.jsonl": True,
        "vendas-2026-01-10-maquina-01-4242.jsonl": True,
        "vendas-2026-05-31-maquina-01-4242.jsonl": False,  # within 30 days of 2026-06-15
        "vendas-2026-02-30.jsonl": False,  # not a date
        "vendas-notas-2026-01-10.jsonl": False,  # another prefix
        "outro-2026-01-10.jsonl": False,
        "vendas-2026-01-10.jsonl.bak": False,
        "vendas-2026-01-10.txt": False,
    }
    for name in names:
        (tmp_path / name).write_text("{}\n", encoding="utf-8")
    (tmp_path / "vendas-2026-01-11.jsonl").mkdir()
    sink = JsonLinesRecordSink(tmp_path, prefix="vendas", retention_days=30)
    assert sink.purge(date(2026, 6, 15)) == 2
    remaining = {path.name for path in tmp_path.iterdir()}
    assert remaining == {name for name, removed in names.items() if not removed} | {
        "vendas-2026-01-11.jsonl"
    }


def test_retention_runs_on_the_first_record_of_a_day(tmp_path: Path) -> None:
    old = tmp_path / "records-2001-01-01-host-1.jsonl"
    old.write_text("{}\n", encoding="utf-8")
    sink = JsonLinesRecordSink(tmp_path, retention_days=1)
    record = _record(tmp_path)
    sink.write(record)
    assert not old.exists()
    old.write_text("{}\n", encoding="utf-8")
    sink.write(record)  # same day: no second purge
    assert old.exists()


def test_retention_needs_to_be_enabled(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="retention is disabled"):
        JsonLinesRecordSink(tmp_path).purge(date(2026, 1, 1))


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"prefix": ""}, "prefix"),
        ({"prefix": "../fora"}, "prefix"),
        ({"prefix": "-x"}, "prefix"),
        ({"retention_days": 0}, "retention_days"),
    ],
)
def test_invalid_arguments(tmp_path: Path, kwargs: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        JsonLinesRecordSink(tmp_path, **kwargs)  # type: ignore[arg-type]


def test_folder_must_exist(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="does not exist"):
        JsonLinesRecordSink(tmp_path / "missing")


def test_fsync_is_optional(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []
    monkeypatch.setattr(os, "fsync", calls.append)
    record = _record(tmp_path)
    JsonLinesRecordSink(tmp_path).write(record)
    assert calls == []
    JsonLinesRecordSink(tmp_path, fsync=True).write(record)
    assert len(calls) == 1
