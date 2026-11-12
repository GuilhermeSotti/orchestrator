from __future__ import annotations

import argparse
from typing import Sequence

from .config_loader import ConfigLoader
from .runner.base import ThreadRunner, ProcessRunner, LocalRunner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="orchestrator")
    parser.add_argument("--spec", required=True, help="Path to the execution specification file")

    return parser


def cli(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    loader = ConfigLoader()
    spec = loader.load_spec(args.spec)

    if spec.runner.get("type") == "thread":
        runner = ThreadRunner()
    elif spec.runner.get("type") == "process":
        runner = ProcessRunner()
    elif spec.runner.get("type") == "local":
        runner = LocalRunner()
    else:
        raise ValueError(f"Unknown runner type: {spec.runner.get('type')}")
    
    result = runner.run(spec)
    print(f"Execution {result.status}: {result.context.status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
