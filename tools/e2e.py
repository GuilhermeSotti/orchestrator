"""End-to-end check: install the built wheels in a clean environment and run the examples.

Usage, from the repository root::

    python -m tools.e2e            # build, install and run in a temporary folder
    python -m tools.e2e --keep     # keep the temporary folder for inspection

The packages and the examples are built as wheels, installed in a new virtual
environment only from those wheels (no package index, no source tree on the
path) and the examples run from a temporary folder, as a consumer project would.
"""

from __future__ import annotations

import argparse
import email
import json
import os
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
import venv
from collections.abc import Mapping, Sequence
from email import policy
from pathlib import Path

from tools.build_packages import PACKAGES, ROOT, build, build_project, source_date_epoch

HELLO = ROOT / "examples" / "hello-automation"
SALES = ROOT / "examples" / "sales-report"
BATCH = ROOT / "examples" / "batch-check"
EXPECTED_BATCH_SUBJECTS = ["Lote conferido", "[batch-check] Execução concluída com sucesso"]
"""Notifications sent by ``batch-check`` for ``examples/batch-check/data``."""
EXPECTED_SALES = {"regions": 3, "orders": 8, "total": "5835.65", "currency": "BRL"}
"""Output of the sales report for ``examples/sales-report/data/pedidos.csv``."""

_DROPPED = frozenset({"PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "VIRTUAL_ENV"})
_PROBE = (
    "import importlib.resources, json\n"
    "import orchestrator_core, orchestrator_sql, orchestrator_sqlite\n"
    "import orchestrator_notifications as n, orchestrator_notifications_smtp as s\n"
    "import orchestrator_notifications_teams as t, orchestrator_records_file as r\n"
    "import orchestrator_calendar as c\n"
    "modules = (orchestrator_core, orchestrator_sql, orchestrator_sqlite, n, s, t, r, c)\n"
    "print(json.dumps({m.__name__: {'file': m.__file__, 'version': m.__version__,\n"
    "    'typed': importlib.resources.files(m).joinpath('py.typed').is_file()}\n"
    "    for m in modules}))\n"
)

_RECORDS = (
    "import json, logging, sys\n"
    "from pathlib import Path\n"
    "from orchestrator_core import RuntimeBuilder\n"
    "from orchestrator_records_file import JsonLinesRecordSink, TextLogHandler\n"
    "root = Path(sys.argv[1])\n"
    "handler = TextLogHandler(root / 'logs')\n"
    "logging.getLogger('e2e').addHandler(handler)\n"
    "logging.getLogger('e2e').setLevel(logging.INFO)\n"
    "sink = JsonLinesRecordSink(root / 'records')\n"
    "def automation(ctx):\n"
    "    with ctx.step('write'):\n"
    "        logging.getLogger('e2e').info('records-file e2e')\n"
    "runtime = RuntimeBuilder().with_environment({}, prefix=None).with_record_sink(sink)\n"
    "result = runtime.build().run(automation)\n"
    "handler.close()\n"
    "logs = sorted(p.relative_to(root).as_posix() for p in root.rglob('*.txt'))\n"
    "lines = [json.loads(line) for p in (root / 'records').iterdir()\n"
    "    for line in p.read_text('utf-8').splitlines()]\n"
    "print(json.dumps({'id': result.execution_id, 'logs': logs, 'records': lines}))\n"
)
"""Uses ``orchestrator-records-file`` from the wheel: one log file and one record line."""
_CALENDAR = (
    "import json, sys\n"
    "from datetime import date\n"
    "from orchestrator_core import RuntimeBuilder\n"
    "from orchestrator_calendar import CalendarCapability\n"
    "settings = {'capabilities': {'calendar': {\n"
    "    'calendars': {'operacao': {'weekend': [], 'layers': ['feriados'],\n"
    "        'coverage': [date.today().year - 1, date.today().year + 1]}},\n"
    "    'sources': {'feriados': {'provider': 'file', 'path': sys.argv[1]}}}}}\n"
    "def automation(ctx):\n"
    "    calendar = ctx.capability(CalendarCapability).get('operacao')\n"
    "    day = date(date.today().year, 12, 24)\n"
    "    return calendar.add_business_days(day, 1).isoformat()\n"
    "runtime = RuntimeBuilder().with_environment({}, prefix=None).with_settings(settings)\n"
    "result = runtime.with_capability(CalendarCapability).build().run(automation)\n"
    "print(json.dumps({'status': result.record.status.value, 'output': result.output}))\n"
)
"""Uses ``orchestrator-calendar`` from the wheel: a holiday file read by the configuration."""


class CheckError(Exception):
    """A step of the end-to-end check failed."""


class SmtpSink(socketserver.ThreadingTCPServer):
    """Local SMTP server that keeps the messages it receives (``batch-check``)."""

    allow_reuse_address = True
    daemon_threads = True

    def __init__(self) -> None:
        """Listen on a free port of the loopback address."""
        super().__init__(("127.0.0.1", 0), _SmtpHandler)
        self.messages: list[str] = []


class _SmtpHandler(socketserver.StreamRequestHandler):
    server: SmtpSink

    def handle(self) -> None:
        self._reply("220 e2e ESMTP")
        data: list[str] | None = None
        while raw := self.rfile.readline():
            line = raw.decode("utf-8", "replace").rstrip("\r\n")
            if data is not None:
                if line == ".":
                    self.server.messages.append("\n".join(data))
                    data = None
                    self._reply("250 queued")
                else:
                    data.append(line[1:] if line.startswith("..") else line)
                continue
            verb = line.partition(" ")[0].upper()
            if verb == "QUIT":
                self._reply("221 bye")
                return
            if verb == "DATA":
                data = []
                self._reply("354 end with .")
            else:
                self._reply("250 ok")

    def _reply(self, text: str) -> None:
        self.wfile.write(f"{text}\r\n".encode())
        self.wfile.flush()


def clean_environment(environ: Mapping[str, str]) -> dict[str, str]:
    """Return a copy of ``environ`` that cannot leak the source tree or local settings.

    Removes the Python path variables, every ``ORCHESTRATOR_*`` and ``PIP_*``
    variable, and makes pip ignore configuration files.
    """
    kept = {
        key: value
        for key, value in environ.items()
        if key.upper() not in _DROPPED and not key.upper().startswith(("ORCHESTRATOR_", "PIP_"))
    }
    return {
        **kept,
        "PIP_CONFIG_FILE": os.devnull,
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PIP_NO_INPUT": "1",
    }


def expected_hello_summary(folder: Path, pattern: str = "*.txt") -> dict[str, int]:
    """Compute, independently of the example, the summary it must produce."""
    totals = {"files": 0, "lines": 0, "words": 0}
    for path in sorted(folder.glob(pattern)):
        text = path.read_text(encoding="utf-8")
        totals["files"] += 1
        totals["lines"] += len(text.splitlines())
        totals["words"] += len(text.split())
    return totals


def expect(condition: bool, message: str) -> None:
    """Raise :class:`CheckError` with ``message`` unless ``condition`` holds."""
    if not condition:
        raise CheckError(message)


def run(command: Sequence[str | Path], *, cwd: Path, env: Mapping[str, str]) -> str:
    """Run ``command`` and return its standard output; raise :class:`CheckError` on failure."""
    arguments = [str(part) for part in command]
    result = subprocess.run(  # noqa: S603 - arguments built by this script, no shell
        arguments,
        cwd=cwd,
        env=dict(env),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        msg = f"exit {result.returncode}: {' '.join(arguments)}\n{result.stdout}{result.stderr}"
        raise CheckError(msg)
    return result.stdout


def build_wheels(dist: Path) -> list[Path]:
    """Build the packages (wheel and sdist) and the examples (wheel) into ``dist``."""
    epoch = source_date_epoch()
    artifacts = [path for package in PACKAGES for path in build(package, dist, epoch)]
    for example in (HELLO, SALES, BATCH):
        artifacts += build_project(example, dist, epoch, sdist=False)
    return artifacts


def create_environment(folder: Path) -> Path:
    """Create a virtual environment with pip only and return its interpreter."""
    venv.EnvBuilder(with_pip=True, clear=True, symlinks=os.name != "nt").create(folder)
    scripts = folder / ("Scripts" if os.name == "nt" else "bin")
    return scripts / ("python.exe" if os.name == "nt" else "python")


def check_installation(
    python: Path, environment: Path, *, cwd: Path, env: Mapping[str, str]
) -> None:
    """Check that the packages come from the environment and ship their typing marker."""
    modules = json.loads(run([python, "-c", _PROBE], cwd=cwd, env=env))
    for name, info in modules.items():
        location = Path(info["file"]).resolve()
        expect(
            location.is_relative_to(environment.resolve()),
            f"{name} imported from outside the clean environment: {location}",
        )
        expect(info["typed"], f"{name} is installed without py.typed")
    for script in ("hello-automation", "sales-report", "batch-check"):
        found = shutil.which(script, path=str(python.parent))
        expect(found is not None, f"console script not installed: {script}")
        run([str(found), "--help"], cwd=cwd, env=env)


def check_hello(python: Path, *, cwd: Path, env: Mapping[str, str]) -> None:
    """Run ``hello-automation`` on its sample data and check the summary."""
    stdout = run(
        [
            python,
            "-m",
            "hello_automation",
            HELLO / "data",
            "--output",
            "summary.json",
            "--config",
            HELLO / "orchestrator.toml",
        ],
        cwd=cwd,
        env=env,
    )
    record = json.loads(stdout)
    expect(record["status"] == "succeeded", f"hello-automation: {record['status']}")
    summary = json.loads((cwd / "summary.json").read_text(encoding="utf-8"))
    expected = expected_hello_summary(HELLO / "data")
    expect(summary == expected, f"hello-automation summary {summary} != {expected}")


def check_sales(python: Path, *, cwd: Path, env: Mapping[str, str]) -> None:
    """Run ``sales-report`` on its sample orders and check the report."""
    stdout = run(
        [
            python,
            "-m",
            "sales_report",
            SALES / "data" / "pedidos.csv",
            "--output",
            "relatorio.csv",
            "--config",
            SALES / "orchestrator.toml",
        ],
        cwd=cwd,
        env=env,
    )
    payload = json.loads(stdout)
    status = payload["record"]["status"]
    expect(status == "succeeded", f"sales-report: {status}")
    expect(payload["output"] == EXPECTED_SALES, f"sales-report output {payload['output']}")
    report = cwd / "relatorio.csv"
    expect(report.is_file() and report.stat().st_size > 0, "sales-report wrote no report")


def check_batch(python: Path, *, cwd: Path, env: Mapping[str, str]) -> None:
    """Run ``batch-check`` against a local SMTP server and check the notifications."""
    with SmtpSink() as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        port = str(server.server_address[1])
        try:
            stdout = run(
                [
                    python,
                    "-m",
                    "batch_check",
                    BATCH / "data",
                    "--config",
                    BATCH / "orchestrator.toml",
                ],
                cwd=cwd,
                env={**env, "ORCHESTRATOR_CAPABILITIES__NOTIFICATIONS__CHANNELS__OPS__PORT": port},
            )
        finally:
            server.shutdown()
            thread.join(timeout=5)
        messages = list(server.messages)
    payload = json.loads(stdout)
    status = payload["record"]["status"]
    expect(status == "succeeded", f"batch-check: {status}")
    expect(
        payload["output"] == {"files": 2, "records": 3}, f"batch-check output {payload['output']}"
    )
    subjects = [email.message_from_string(m, policy=policy.default)["Subject"] for m in messages]
    expect(subjects == EXPECTED_BATCH_SUBJECTS, f"batch-check notifications {subjects}")


def check_records(python: Path, *, cwd: Path, env: Mapping[str, str]) -> None:
    """Write a log file and an execution record with ``orchestrator-records-file``."""
    root = cwd / "records-file"
    (root / "logs").mkdir(parents=True)
    (root / "records").mkdir()
    payload = json.loads(run([python, "-c", _RECORDS, root], cwd=cwd, env=env))
    logs, records = payload["logs"], payload["records"]
    expect(len(logs) == 1, f"records-file wrote {len(logs)} log files")
    expect(logs[0].startswith("logs/execute_automation/write/"), f"log file {logs[0]}")
    expect(len(records) == 1, f"records-file wrote {len(records)} records")
    expect(records[0]["execution_id"] == payload["id"], "record of another execution")
    expect(records[0]["status"] == "succeeded", f"record status {records[0]['status']}")


def check_calendar(python: Path, *, cwd: Path, env: Mapping[str, str]) -> None:
    """Read a holiday file through ``orchestrator-calendar`` and compute a business day."""
    year = time.localtime().tm_year
    holidays = cwd / "feriados.csv"
    holidays.write_text(f"date,type,name\n{year}-12-25,holiday,Natal\n", encoding="utf-8")
    payload = json.loads(run([python, "-c", _CALENDAR, holidays], cwd=cwd, env=env))
    expect(payload["status"] == "succeeded", f"calendar: {payload['status']}")
    expected = f"{year}-12-26"  # empty weekend: only the holiday is skipped
    expect(payload["output"] == expected, f"calendar output {payload['output']} != {expected}")


def install(python: Path, dist: Path, *, cwd: Path, env: Mapping[str, str]) -> None:
    """Install the examples, the packages they use and the file destinations from ``dist``."""
    run(
        [
            python,
            "-m",
            "pip",
            "install",
            "--no-index",
            "--only-binary",
            ":all:",
            "--find-links",
            dist,
            "hello-automation",
            "sales-report",
            "batch-check",
            "orchestrator-records-file",
            "orchestrator-calendar",
        ],
        cwd=cwd,
        env=env,
    )
    run([python, "-m", "pip", "check"], cwd=cwd, env=env)


def check(base: Path) -> None:
    """Run every step inside ``base``; raise :class:`CheckError` on the first failure."""
    dist, environment, work = base / "dist", base / "env", base / "work"
    work.mkdir(parents=True)
    env = clean_environment(os.environ)
    build_wheels(dist)
    sys.stdout.write("ok: wheels built\n")
    python = create_environment(environment)
    sys.stdout.write("ok: clean virtual environment\n")
    install(python, dist, cwd=work, env=env)
    sys.stdout.write("ok: installed from the wheels only, pip check clean\n")
    check_installation(python, environment, cwd=work, env=env)
    sys.stdout.write("ok: packages, typing markers and console scripts\n")
    check_hello(python, cwd=work, env=env)
    sys.stdout.write("ok: hello-automation\n")
    check_sales(python, cwd=work, env=env)
    sys.stdout.write("ok: sales-report\n")
    check_batch(python, cwd=work, env=env)
    sys.stdout.write("ok: batch-check (notifications through a local SMTP server)\n")
    check_records(python, cwd=work, env=env)
    sys.stdout.write("ok: records-file (log file and execution record)\n")
    check_calendar(python, cwd=work, env=env)
    sys.stdout.write("ok: calendar (holiday file and business days)\n")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the end-to-end check and return the process exit code."""
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--keep", action="store_true", help="keep the temporary folder")
    args = parser.parse_args(argv)
    base = Path(tempfile.mkdtemp(prefix="orchestrator-e2e-"))
    try:
        check(base)
    except CheckError as exc:
        sys.stderr.write(f"e2e failed: {exc}\n")
        return 1
    finally:
        if args.keep:
            sys.stdout.write(f"kept: {base}\n")
        else:
            shutil.rmtree(base, ignore_errors=True)
    sys.stdout.write("e2e ok\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
