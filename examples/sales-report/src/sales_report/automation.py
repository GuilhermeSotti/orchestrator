"""Automation of the example: sales report by region, staged in SQL.

Business rules (columns of the CSV, filters, report format) live here, in the
consumer project. The SQL Capability only offers safe, parameterized access.
"""

from __future__ import annotations

import csv
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from orchestrator_core import ExecutionContext
from orchestrator_sql import Column, SqlCapability, SqlType, Table

ORDERS = Table.define(
    "pedidos",
    [
        Column("id", SqlType.INTEGER, primary_key=True),
        Column("cliente", SqlType.TEXT, nullable=False),
        Column("regiao", SqlType.TEXT, nullable=False),
        Column("valor", SqlType.NUMERIC, nullable=False),
        Column("data", SqlType.DATE, nullable=False),
    ],
)

REPORT_QUERY = """
SELECT regiao, count(*) AS pedidos, sum(valor) AS total
FROM pedidos
WHERE valor >= :minimo
GROUP BY regiao
ORDER BY regiao
"""


@dataclass(frozen=True, slots=True)
class Parameters:
    """Validated parameters of :func:`build_sales_report`."""

    orders_file: Path
    output_file: Path
    minimum_amount: Decimal = Decimal(0)

    @classmethod
    def validate(cls, raw: Mapping[str, object]) -> Parameters:
        """Convert and check the raw parameters.

        Raises:
            ValueError: If a parameter is missing or invalid.
        """
        try:
            orders_file = Path(str(raw["orders_file"]))
            output_file = Path(str(raw["output_file"]))
            minimum = Decimal(str(raw.get("minimum_amount", "0")))
        except KeyError as exc:
            msg = f"missing parameter: {exc.args[0]}"
            raise ValueError(msg) from None
        except InvalidOperation:
            msg = "minimum_amount must be a number"
            raise ValueError(msg) from None
        if not orders_file.is_file():
            msg = f"orders file not found: {orders_file}"
            raise ValueError(msg)
        return cls(orders_file=orders_file, output_file=output_file, minimum_amount=minimum)


def read_orders(path: Path) -> list[dict[str, object]]:
    """Read and validate the orders CSV.

    Raises:
        ValueError: If a line is invalid; the message tells which line.
    """
    orders: list[dict[str, object]] = []
    with path.open(encoding="utf-8", newline="") as handle:
        for line, row in enumerate(csv.DictReader(handle), start=2):
            try:
                orders.append(
                    {
                        "id": int(row["id"]),
                        "cliente": row["cliente"].strip(),
                        "regiao": row["regiao"].strip(),
                        "valor": Decimal(row["valor"]),
                        "data": date.fromisoformat(row["data"]),
                    }
                )
            except (KeyError, ValueError, InvalidOperation, AttributeError) as exc:
                msg = f"{path.name}, line {line}: invalid order ({type(exc).__name__})"
                raise ValueError(msg) from exc
    return orders


def build_sales_report(ctx: ExecutionContext) -> dict[str, object]:
    """Load the orders into SQL, aggregate by region and write the report CSV."""
    params = ctx.parameters_as(Parameters)
    currency = ctx.config.section("app").get_str("currency", "BRL")
    orders = read_orders(params.orders_file)
    ctx.logger.info("%d orders read from %s", len(orders), params.orders_file.name)

    sql = ctx.capability(SqlCapability)
    sql.create_table(ORDERS)
    with sql.transaction():
        sql.insert_many(ORDERS.name, orders)
    ctx.check()
    rows = sql.fetch_all(REPORT_QUERY, {"minimo": params.minimum_amount})

    params.output_file.parent.mkdir(parents=True, exist_ok=True)
    with params.output_file.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["regiao", "pedidos", f"total_{currency.lower()}"])
        for row in rows:
            writer.writerow([row["regiao"], row["pedidos"], f"{Decimal(str(row['total'])):.2f}"])
    total = sum((Decimal(str(row["total"])) for row in rows), Decimal(0))
    ctx.logger.info("report written to %s", params.output_file)
    return {
        "regions": len(rows),
        "orders": sum(int(row["pedidos"]) for row in rows),
        "total": f"{total:.2f}",
        "currency": currency,
    }
