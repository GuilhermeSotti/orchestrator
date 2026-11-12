"""Command line: ``python -m sales_report data/pedidos.csv --output relatorio.csv``."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from orchestrator_core import Runtime, RuntimeBuilder
from orchestrator_core.logs import configure_logging
from orchestrator_sql import SqlCapability
from orchestrator_sqlite import SqliteProvider
from sales_report.automation import Parameters, build_sales_report

PROVIDERS = {"sqlite": SqliteProvider}
"""SQL Providers this project allows the configuration to choose from."""


def build_runtime(config: str | None) -> Runtime:
    """Compose the Runtime of this project (the composition root)."""
    builder = RuntimeBuilder()
    if config:
        builder.with_config_file(config)
    return builder.with_capability(SqlCapability, providers=PROVIDERS).build()


def main(argv: Sequence[str] | None = None) -> int:
    """Run the report once and print its record; return the process exit code."""
    parser = argparse.ArgumentParser(prog="sales-report", description=__doc__)
    parser.add_argument("orders_file", help="CSV with the orders")
    parser.add_argument("--output", default="relatorio.csv", help="where to write the report")
    parser.add_argument("--minimum", default="0", help="ignore orders below this amount")
    parser.add_argument("--config", default="orchestrator.toml", help="TOML configuration file")
    parser.add_argument("--json-logs", action="store_true", help="log as JSON lines")
    args = parser.parse_args(argv)

    configure_logging("INFO", json_output=args.json_logs)
    result = build_runtime(args.config).run(
        build_sales_report,
        name="sales-report",
        parameters={
            "orders_file": args.orders_file,
            "output_file": args.output,
            "minimum_amount": args.minimum,
        },
        parameters_validator=Parameters.validate,
    )
    print(json.dumps({"record": result.record.to_dict(), "output": result.output}, indent=2))
    return 0 if result.succeeded else 1


if __name__ == "__main__":
    raise SystemExit(main())
