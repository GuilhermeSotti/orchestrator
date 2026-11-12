"""Command line of the example: ``python -m hello_automation <folder> --output summary.json``."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from hello_automation.automation import Parameters, summarize_texts
from orchestrator_core import RuntimeBuilder
from orchestrator_core.logs import configure_logging


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
    result = runtime.run(
        summarize_texts,
        name="summarize-texts",
        parameters={"input_dir": args.input_dir, "output_file": args.output},
        parameters_validator=Parameters.validate,
    )
    print(json.dumps(result.record.to_dict(), indent=2))
    return 0 if result.succeeded else 1


if __name__ == "__main__":
    raise SystemExit(main())
