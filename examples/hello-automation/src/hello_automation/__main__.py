"""Command line of the example: ``python -m hello_automation <folder> --output summary.json``."""

from __future__ import annotations

import argparse
import json
import signal
from collections.abc import Sequence

from hello_automation.automation import Parameters, summarize_texts
from orchestrator_core import CancellationToken, RuntimeBuilder
from orchestrator_core.logs import configure_logging


def cancel_on_signals(token: CancellationToken) -> dict[int, object]:
    """Turn termination requests into cancellation, so that teardown runs (RFC-0005, 2.4).

    The Core never installs signal handlers: the process belongs to the
    application. Returns the previous handlers, to be restored after the run.
    """
    previous: dict[int, object] = {}
    for name in ("SIGTERM", "SIGBREAK"):  # SIGBREAK: Ctrl+Break on Windows
        number = getattr(signal, name, None)
        if number is not None:
            previous[number] = signal.signal(number, lambda *_, n=name: token.cancel(n))
    return previous


def restore_signals(previous: dict[int, object]) -> None:
    """Reinstall the handlers returned by :func:`cancel_on_signals`."""
    for number, handler in previous.items():
        signal.signal(number, handler)  # type: ignore[arg-type]


def main(argv: Sequence[str] | None = None) -> int:
    """Run the automation once and print its record; return the process exit code."""
    parser = argparse.ArgumentParser(prog="hello-automation", description=__doc__)
    parser.add_argument("input_dir", help="folder with .txt files")
    parser.add_argument("--output", default="summary.json", help="where to write the summary")
    parser.add_argument("--config", default=None, help="TOML configuration file")
    parser.add_argument("--json-logs", action="store_true", help="log as JSON lines")
    args = parser.parse_args(argv)

    configure_logging("INFO", json_output=args.json_logs)
    builder = RuntimeBuilder()
    if args.config:
        builder.with_config_file(args.config)
    runtime = builder.build()
    token = CancellationToken()
    previous = cancel_on_signals(token)
    try:
        result = runtime.run(
            summarize_texts,
            name="summarize-texts",
            parameters={"input_dir": args.input_dir, "output_file": args.output},
            parameters_validator=Parameters.validate,
            cancellation=token,
        )
    finally:
        restore_signals(previous)
    print(json.dumps(result.record.to_dict(), indent=2))
    return 0 if result.succeeded else 1


if __name__ == "__main__":
    raise SystemExit(main())
