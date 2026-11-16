"""Termination by signal (RFC-0005, 2.4): the recipe of the guide leads to teardown and Finished.

The Core installs no signal handler. These tests run, in a child process, the
recipe documented in ``docs/guides/encerramento-por-sinal.md`` and check that a
termination request ends the execution as ``cancelled``, with the finalizer run
and ``ExecutionFinished`` published.
"""

from __future__ import annotations

import json
import os
import queue
import signal
import subprocess
import sys
import threading
from pathlib import Path

import pytest

import orchestrator_core

CHILD = r"""
import json
import signal

from orchestrator_core import CancellationToken, ExecutionFinished, RuntimeBuilder

token = CancellationToken()
signal.signal(signal.SIGTERM, lambda *_: token.cancel("SIGTERM"))
if hasattr(signal, "SIGBREAK"):  # Windows: Ctrl+Break
    signal.signal(signal.SIGBREAK, lambda *_: token.cancel("SIGBREAK"))

finished = []
runtime = (
    RuntimeBuilder()
    .with_environment({}, prefix=None)
    .on_event(ExecutionFinished, lambda event: finished.append(event.status.value))
    .build()
)


def automation(ctx):
    ctx.add_finalizer(lambda outcome: print("finalizer", outcome.status.value, flush=True))
    print("ready", flush=True)
    for _ in range(600):  # at most about 30 s
        ctx.sleep(0.05)


result = runtime.run(automation, name="signal-test", cancellation=token)
print(json.dumps({"status": result.status.value, "finished": finished, "reason": token.reason}))
"""


def _reader(stream: object, lines: queue.Queue[str]) -> None:
    for line in stream:  # type: ignore[attr-defined]
        lines.put(line.rstrip("\r\n"))
    lines.put("")  # end of output


def test_termination_signal_cancels_runs_teardown_and_publishes_finished() -> None:
    windows = sys.platform == "win32"
    source = Path(orchestrator_core.__file__).resolve().parents[1]
    env = {**os.environ, "PYTHONPATH": str(source), "PYTHONUTF8": "1"}
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if windows else 0  # type: ignore[attr-defined]
    with subprocess.Popen(  # noqa: S603 - fixed command: this interpreter and a constant script
        [sys.executable, "-c", CHILD],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
        creationflags=flags,
    ) as process:
        lines: queue.Queue[str] = queue.Queue()
        reader = threading.Thread(target=_reader, args=(process.stdout, lines), daemon=True)
        reader.start()
        output: list[str] = []
        try:
            first = lines.get(timeout=60)
            output.append(first)
            assert first == "ready", output
            if windows:
                try:
                    process.send_signal(signal.CTRL_BREAK_EVENT)  # type: ignore[attr-defined]
                except OSError as exc:  # pragma: no cover - depends on the console of the runner
                    pytest.skip(f"cannot deliver CTRL_BREAK_EVENT here: {exc}")
            else:
                process.send_signal(signal.SIGTERM)
            assert process.wait(timeout=60) == 0
            while (line := lines.get(timeout=10)) != "":
                output.append(line)
            reader.join(timeout=10)
        finally:
            if process.poll() is None:  # pragma: no cover - only when an assertion failed
                process.kill()
    report = json.loads(output[-1])
    expected_reason = "SIGBREAK" if windows else "SIGTERM"
    assert "finalizer cancelled" in output, output
    assert report == {"status": "cancelled", "finished": ["cancelled"], "reason": expected_reason}
