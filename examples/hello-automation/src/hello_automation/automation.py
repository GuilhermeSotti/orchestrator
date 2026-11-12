"""Automation of the example: summarize the text files of a folder.

Everything here is business logic of the consumer project. The Orchestrator
provides the lifecycle, configuration, workspace, logging and cancellation.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from orchestrator_core import ExecutionContext


@dataclass(frozen=True, slots=True)
class Parameters:
    """Validated parameters of :func:`summarize_texts`."""

    input_dir: Path
    output_file: Path

    @classmethod
    def validate(cls, raw: Mapping[str, object]) -> Parameters:
        """Convert and check the raw parameters.

        Raises:
            ValueError: If a parameter is missing or the input folder does not exist.
        """
        try:
            input_dir = Path(str(raw["input_dir"]))
            output_file = Path(str(raw["output_file"]))
        except KeyError as exc:
            msg = f"missing parameter: {exc.args[0]}"
            raise ValueError(msg) from None
        if not input_dir.is_dir():
            msg = f"input folder not found: {input_dir}"
            raise ValueError(msg)
        return cls(input_dir=input_dir, output_file=output_file)


def summarize_texts(ctx: ExecutionContext) -> dict[str, int]:
    """Count files, lines and words, and write the summary as JSON."""
    params = ctx.parameters_as(Parameters)
    pattern = ctx.config.section("app").get_str("pattern", "*.txt")
    totals = {"files": 0, "lines": 0, "words": 0}
    for path in sorted(params.input_dir.glob(pattern)):
        ctx.check()
        text = path.read_text(encoding="utf-8")
        totals["files"] += 1
        totals["lines"] += len(text.splitlines())
        totals["words"] += len(text.split())
        ctx.logger.info("processed %s", path.name)
    draft = ctx.workspace / "summary.json"
    draft.write_text(json.dumps(totals, indent=2) + "\n", encoding="utf-8")
    params.output_file.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(draft, params.output_file)
    return totals
