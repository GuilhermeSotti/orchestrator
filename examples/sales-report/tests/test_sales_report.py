from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from orchestrator_core import ExecutionStatus, RuntimeBuilder, StageStatus
from orchestrator_sql import SqlCapability
from orchestrator_sqlite import SqliteProvider
from sales_report import Parameters, build_sales_report
from sales_report.__main__ import main

ROOT = Path(__file__).resolve().parents[1]
ORDERS = ROOT / "data" / "pedidos.csv"
CONFIG = ROOT / "orchestrator.toml"


def runtime(environ: dict[str, str] | None = None) -> RuntimeBuilder:
    return (
        RuntimeBuilder()
        .with_config_file(CONFIG)
        .with_environment(environ or {})
        .with_capability(SqlCapability, providers={"sqlite": SqliteProvider})
    )


def report(path: Path) -> list[list[str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.reader(handle))


def test_report_in_memory(tmp_path: Path) -> None:
    output = tmp_path / "relatorio.csv"
    result = (
        runtime()
        .build()
        .run(
            build_sales_report,
            parameters={"orders_file": str(ORDERS), "output_file": str(output)},
            parameters_validator=Parameters.validate,
        )
    )
    result.raise_for_status()
    assert result.output == {"regions": 3, "orders": 8, "total": "5835.65", "currency": "BRL"}
    assert report(output) == [
        ["regiao", "pedidos", "total_brl"],
        ["Nordeste", "2", "2145.00"],
        ["Sudeste", "3", "820.40"],
        ["Sul", "3", "2870.25"],
    ]


def test_minimum_amount_is_a_parameter(tmp_path: Path) -> None:
    result = (
        runtime()
        .build()
        .run(
            build_sales_report,
            parameters={
                "orders_file": str(ORDERS),
                "output_file": str(tmp_path / "r.csv"),
                "minimum_amount": "500",
            },
            parameters_validator=Parameters.validate,
        )
    )
    assert result.output == {"regions": 2, "orders": 4, "total": "4970.25", "currency": "BRL"}


def test_database_is_chosen_by_configuration_only(tmp_path: Path) -> None:
    """E4.4 (partial): switching the database is a configuration change, not a code change."""
    database = tmp_path / "vendas.db"
    built = runtime({"ORCHESTRATOR_CAPABILITIES__SQL__DATABASE": str(database)}).build()
    result = built.run(
        build_sales_report,
        parameters={"orders_file": str(ORDERS), "output_file": str(tmp_path / "r.csv")},
        parameters_validator=Parameters.validate,
    )
    result.raise_for_status()
    assert database.exists()
    persisted = built.run(
        lambda ctx: ctx.capability(SqlCapability).scalar("SELECT count(*) FROM pedidos")
    )
    assert persisted.output == 8  # the data outlived the execution: it is in the file


def test_invalid_orders_fail_with_the_line_number(tmp_path: Path) -> None:
    broken = tmp_path / "pedidos.csv"
    broken.write_text(
        "id,cliente,regiao,valor,data\n1,A,Sul,10,2026-11-01\n2,B,Sul,dez,2026-11-02\n",
        encoding="utf-8",
    )
    result = (
        runtime()
        .build()
        .run(
            build_sales_report,
            parameters={"orders_file": str(broken), "output_file": str(tmp_path / "r.csv")},
            parameters_validator=Parameters.validate,
        )
    )
    assert result.status is ExecutionStatus.FAILED
    assert result.stage("execute_automation").status is StageStatus.FAILED
    assert "pedidos.csv, line 3: invalid order" in str(result.error)


@pytest.mark.parametrize(
    ("parameters", "message"),
    [
        ({"output_file": "x.csv"}, "missing parameter: orders_file"),
        ({"orders_file": "nope.csv", "output_file": "x.csv"}, "orders file not found"),
        (
            {"orders_file": str(ORDERS), "output_file": "x.csv", "minimum_amount": "abc"},
            "minimum_amount must be a number",
        ),
    ],
)
def test_parameter_validation(parameters: dict[str, str], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        Parameters.validate(parameters)


def test_command_line(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    output = tmp_path / "relatorio.csv"
    code = main([str(ORDERS), "--output", str(output), "--minimum", "100", "--config", str(CONFIG)])
    assert code == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["record"]["status"] == "succeeded"
    assert printed["output"]["orders"] == 6
    assert main(["missing.csv", "--config", str(CONFIG)]) == 1
