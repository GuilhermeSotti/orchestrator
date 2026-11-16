"""Several real processes writing to the same folders at the same time (RFC-0009, answer 5)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

PROCESSES = 4
EXECUTIONS = 20
LINES = 100

WORKER = r"""
import logging
import sys
import time
from pathlib import Path

from orchestrator_core import RuntimeBuilder
from orchestrator_records_file import JsonLinesRecordSink, TextLogHandler

root, marker = Path(sys.argv[1]), sys.argv[2]
executions, lines = int(sys.argv[3]), int(sys.argv[4])
logger = logging.getLogger("worker")
logger.setLevel(logging.INFO)
logger.propagate = False
handler = TextLogHandler(root / "logs")
logger.addHandler(handler)
sink = JsonLinesRecordSink(root / "records", retention_days=30)
runtime = RuntimeBuilder().with_environment({}, prefix=None).with_record_sink(sink).build()


def automation(ctx):
    with ctx.step("work"):
        for line in range(lines):
            logger.info("%s %04d", marker, line)


(root / f"ready-{marker}").touch()
deadline = time.monotonic() + 60
while not (root / "go").exists():
    if time.monotonic() > deadline:
        sys.exit("timed out waiting for the start signal")
    time.sleep(0.001)
for _ in range(executions):
    if not runtime.run(automation).succeeded:
        sys.exit("execution failed")
handler.close()
"""


def _old(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("old\n", encoding="utf-8")
    return path


@pytest.mark.slow
def test_processes_write_to_the_same_folders_at_once(tmp_path: Path) -> None:
    (tmp_path / "logs").mkdir()
    (tmp_path / "records").mkdir()
    old = [  # every process purges on its first line: concurrent removals must not fail
        _old(tmp_path / "logs" / "execute_automation" / "work" / "2001/01/01/h_u_1.txt"),
        _old(tmp_path / "logs" / "_" / "_" / "2001/01/02/h_u_2.txt"),
        _old(tmp_path / "records" / "records-2001-01-01-h-1.jsonl"),
    ]
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(path for path in sys.path if path)}
    counts = [str(EXECUTIONS), str(LINES)]
    processes = [
        subprocess.Popen(  # noqa: S603 - fixed interpreter and arguments, no shell
            [sys.executable, "-c", WORKER, str(tmp_path), f"p{number}", *counts],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for number in range(PROCESSES)
    ]
    try:
        deadline = time.monotonic() + 60
        while len(list(tmp_path.glob("ready-*"))) < PROCESSES:
            assert all(process.poll() is None for process in processes), "a worker exited early"
            assert time.monotonic() < deadline, "workers did not start"
            time.sleep(0.01)
        (tmp_path / "go").touch()
        outputs = [process.communicate(timeout=120) for process in processes]
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
    assert [process.returncode for process in processes] == [0] * PROCESSES, outputs
    assert all(stderr == "" for _, stderr in outputs), outputs  # no handleError traceback

    log_files = sorted((tmp_path / "logs").rglob("*.txt"))
    assert len(log_files) == PROCESSES
    markers = set()
    spans = []
    for path in log_files:
        assert path.relative_to(tmp_path / "logs").parts[:2] == ("execute_automation", "work")
        tokens = [line.split()[-2:] for line in path.read_text("utf-8").splitlines()]
        assert len({marker for marker, _ in tokens}) == 1
        assert [int(number) for _, number in tokens] == list(range(LINES)) * EXECUTIONS
        markers.add(tokens[0][0])
        lines = path.read_text("utf-8").splitlines()
        spans.append((lines[0][:23], lines[-1][:23]))  # UTC times with milliseconds
    assert markers == {f"p{number}" for number in range(PROCESSES)}
    assert max(first for first, _ in spans) < min(last for _, last in spans)  # all wrote at once

    record_files = sorted((tmp_path / "records").glob("records-*.jsonl"))
    assert len(record_files) == PROCESSES
    for path in record_files:
        lines = [json.loads(line) for line in path.read_text("utf-8").splitlines()]
        assert [line["status"] for line in lines] == ["succeeded"] * EXECUTIONS
    assert not any(path.exists() for path in old)
