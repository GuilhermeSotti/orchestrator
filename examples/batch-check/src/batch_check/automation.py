"""Automation of the example: every batch file of a folder must have records.

Business logic of the consumer project. The notifications Capability sends
the lifecycle notices (configured in ``orchestrator.toml``) and the summary
written here; the texts of the summary belong to the consumer.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from orchestrator_core import ExecutionContext
from orchestrator_notifications import Notification, NotificationCapability


@dataclass(frozen=True, slots=True)
class Parameters:
    """Validated parameters of :func:`check_batch`."""

    input_dir: Path

    @classmethod
    def validate(cls, raw: Mapping[str, object]) -> Parameters:
        """Convert and check the raw parameters.

        Raises:
            ValueError: If the input folder is missing or does not exist.
        """
        try:
            input_dir = Path(str(raw["input_dir"]))
        except KeyError as exc:
            msg = f"missing parameter: {exc.args[0]}"
            raise ValueError(msg) from None
        if not input_dir.is_dir():
            msg = f"input folder not found: {input_dir}"
            raise ValueError(msg)
        return cls(input_dir=input_dir)


def check_batch(ctx: ExecutionContext) -> dict[str, int]:
    """Count the records of every ``*.txt`` file; an empty file fails the execution."""
    params = ctx.parameters_as(Parameters)
    files = sorted(params.input_dir.glob("*.txt"))
    records = 0
    empty: list[str] = []
    for path in files:
        ctx.check()
        with ctx.step("check_file"):
            lines = path.read_text(encoding="utf-8").splitlines()[1:]  # first line: header
            if not lines:
                empty.append(path.name)
            records += len(lines)
    if empty:
        msg = f"batch files without records: {', '.join(empty)}"
        raise ValueError(msg)
    notifier = ctx.capability(NotificationCapability)
    if notifier.default_channels:  # without channels in the configuration, nothing is sent
        notifier.send(
            Notification(
                subject="Lote conferido",
                body=f"Foram conferidos {len(files)} arquivo(s), com {records} registro(s).",
                facts=(("Arquivos", str(len(files))), ("Registros", str(records))),
                kind="batch.checked",
            )
        )
    return {"files": len(files), "records": records}
