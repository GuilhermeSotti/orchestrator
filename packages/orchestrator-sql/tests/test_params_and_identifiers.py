from __future__ import annotations

import pytest

from orchestrator_sql import (
    Column,
    SqlProgrammingError,
    SqlType,
    Table,
    TableName,
    placeholder_names,
    translate,
    validate_identifier,
)

SQL = """
SELECT ':not_a_param', "col:umn", amount::numeric -- comment :ignored
FROM t /* block :ignored */
WHERE a = :a AND b = :b AND again = :a AND note LIKE '%x%' AND it = 'it''s :x'
"""


def test_placeholders_skip_literals_comments_and_casts() -> None:
    assert placeholder_names(SQL) == ("a", "b", "a")
    assert placeholder_names("SELECT 1") == ()
    assert placeholder_names("SELECT :1, :_ok") == ("_ok",)
    assert placeholder_names("SELECT 'unterminated :x") == ()
    assert placeholder_names("SELECT 1 /* unterminated :x") == ()


@pytest.mark.parametrize(
    ("style", "expected_sql", "expected_params"),
    [
        ("named", "x = :a AND y = :b AND z = :a AND p LIKE '%'", {"a": 1, "b": 2}),
        ("qmark", "x = ? AND y = ? AND z = ? AND p LIKE '%'", (1, 2, 1)),
        ("numeric", "x = :1 AND y = :2 AND z = :1 AND p LIKE '%'", (1, 2)),
        ("format", "x = %s AND y = %s AND z = %s AND p LIKE '%%'", (1, 2, 1)),
        (
            "pyformat",
            "x = %(a)s AND y = %(b)s AND z = %(a)s AND p LIKE '%%'",
            {"a": 1, "b": 2},
        ),
    ],
)
def test_translation_to_every_paramstyle(
    style: str, expected_sql: str, expected_params: object
) -> None:
    sql = "x = :a AND y = :b AND z = :a AND p LIKE '%'"
    assert translate(sql, {"a": 1, "b": 2}, style) == (expected_sql, expected_params)


def test_translation_errors_name_parameters_but_never_values() -> None:
    with pytest.raises(SqlProgrammingError, match="missing SQL parameter\\(s\\): b"):
        translate("SELECT :a, :b", {"a": "secret-value"}, "named")
    with pytest.raises(SqlProgrammingError, match="unused SQL parameter\\(s\\): typo") as info:
        translate("SELECT :a", {"a": 1, "typo": "secret-value"}, "named")
    assert "secret-value" not in str(info.value)
    with pytest.raises(SqlProgrammingError, match="unsupported DB-API paramstyle"):
        translate("SELECT 1", None, "weird")


@pytest.mark.parametrize("name", ["orders", "_tmp", "Order_2026", "a" * 63])
def test_valid_identifiers(name: str) -> None:
    assert validate_identifier(name) == name


@pytest.mark.parametrize(
    "name",
    ["", "1abc", "users; DROP TABLE x", 'a"b', "a b", "a-b", "a" * 64, "naïve", None],
)
def test_invalid_identifiers_are_rejected(name: str) -> None:
    with pytest.raises(SqlProgrammingError, match="invalid SQL identifier"):
        validate_identifier(name)


def test_table_names() -> None:
    assert TableName.parse("orders") == TableName("orders")
    assert TableName.parse("sales.orders") == TableName("orders", "sales")
    assert str(TableName("orders", "sales")) == "sales.orders"
    assert TableName.parse(TableName("x")) == TableName("x")
    with pytest.raises(SqlProgrammingError, match="invalid table name"):
        TableName.parse("a.b.c")
    with pytest.raises(SqlProgrammingError):
        TableName.parse("sales.or ders")


def test_table_definitions_are_validated() -> None:
    with pytest.raises(SqlProgrammingError, match="has no columns"):
        Table.define("t", [])
    with pytest.raises(SqlProgrammingError, match="duplicate column names"):
        Table.define("t", [Column("id", SqlType.INTEGER), Column("ID", SqlType.TEXT)])
    with pytest.raises(SqlProgrammingError):
        Column("bad name", SqlType.TEXT)
