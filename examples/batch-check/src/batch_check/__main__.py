"""Command line of the example: ``python -m batch_check <folder> --config orchestrator.toml``."""

from __future__ import annotations

import argparse
import json
import signal
from collections.abc import Mapping, Sequence

from batch_check.automation import Parameters, check_batch
from orchestrator_core import CancellationToken, Runtime, RuntimeBuilder
from orchestrator_core.logs import configure_logging
from orchestrator_notifications import (
    NotificationCapability,
    NotificationChannel,
    NotifyOutcome,
    NotifyStarted,
)
from orchestrator_notifications_smtp import SmtpChannel
from orchestrator_notifications_teams import TeamsWebhookChannel

CHANNELS: Mapping[str, type[NotificationChannel]] = {
    "smtp": SmtpChannel,
    "teams": TeamsWebhookChannel,
}
"""Channel Providers the configuration may choose."""


def build_runtime(
    config: str | None, channels: Mapping[str, type[NotificationChannel]] = CHANNELS
) -> Runtime:
    """Register the notifications Capability first and install the lifecycle stages."""
    builder = RuntimeBuilder()
    if config:
        builder.with_config_file(config)
    return (
        builder.with_capability(NotificationCapability, providers=channels)
        .with_stage(NotifyStarted(), after="prepare_execution")
        .with_stage(NotifyOutcome(), after="finalize")
        .build()
    )


def cancel_on_signals(token: CancellationToken) -> dict[int, object]:
    """Turn termination requests into cancellation, so that teardown runs (RFC-0005, 2.4)."""
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
    """Run the automation once and print the record; return the process exit code."""
    parser = argparse.ArgumentParser(prog="batch-check", description=__doc__)
    parser.add_argument("input_dir", help="folder with the batch files (*.txt)")
    parser.add_argument("--config", default=None, help="TOML configuration file")
    parser.add_argument("--json-logs", action="store_true", help="log as JSON lines")
    args = parser.parse_args(argv)

    configure_logging("INFO", json_output=args.json_logs)
    runtime = build_runtime(args.config)
    token = CancellationToken()
    previous = cancel_on_signals(token)
    try:
        result = runtime.run(
            check_batch,
            name="batch-check",
            parameters={"input_dir": args.input_dir},
            parameters_validator=Parameters.validate,
            cancellation=token,
        )
    finally:
        restore_signals(previous)
    print(json.dumps({"record": result.record.to_dict(), "output": result.output}, indent=2))
    return 0 if result.succeeded else 1


if __name__ == "__main__":
    raise SystemExit(main())
