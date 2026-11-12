from __future__ import annotations

from pathlib import Path

import pytest

from orchestrator_core import (
    ConfigSection,
    Configuration,
    ConfigurationError,
    RuntimeBuilder,
    SecretRef,
)
from orchestrator_core._config import environment_tree


def write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("file_value", "env_value", "override", "expected"),
    [
        (None, None, None, None),
        ("10", None, None, 10.0),
        ("10", "20", None, 20.0),
        ("10", "20", 30, 30.0),
        (None, None, 30, 30.0),
        (None, "20", None, 20.0),
    ],
)
def test_precedence_defaults_file_environment_explicit(
    tmp_path: Path,
    file_value: str | None,
    env_value: str | None,
    override: int | None,
    expected: float | None,
) -> None:
    text = f"[runtime]\ntimeout = {file_value}\n" if file_value else ""
    file = write(tmp_path / "orchestrator.toml", text)
    environ = {"ORCHESTRATOR_RUNTIME__TIMEOUT": env_value} if env_value else {}
    builder = RuntimeBuilder().with_config_file(file).with_environment(environ)
    if override is not None:
        builder.with_settings({"runtime": {"timeout": override}})
    assert builder.build().configuration.runtime.timeout == expected


def test_environment_tree_rules() -> None:
    environ = {
        "orchestrator_runtime__name": "lower-case-prefix",
        "ORCHESTRATOR_CAPABILITIES__SQL__DATABASE": "app.db",
        "ORCHESTRATOR_HOME": "/ignored-no-separator",
        "OTHER_RUNTIME__NAME": "ignored-other-prefix",
    }
    assert environment_tree(environ, "ORCHESTRATOR") == {
        "runtime": {"name": "lower-case-prefix"},
        "capabilities": {"sql": {"database": "app.db"}},
    }
    with pytest.raises(ConfigurationError, match="invalid configuration variable"):
        environment_tree({"ORCHESTRATOR_RUNTIME____NAME": "x"}, "ORCHESTRATOR")


def test_typed_accessors_convert_strings_and_name_the_key() -> None:
    section = ConfigSection(
        {
            "text": "abc",
            "count": "7",
            "ratio": "0.5",
            "flag": "Yes",
            "off": "0",
            "path": "~/data",
            "mode": "fast",
            "password": "env:DB_PASSWORD",
            "native_int": 3,
            "native_bool": True,
        },
        "capabilities.demo",
    )
    assert section.get_str("text") == "abc"
    assert section.get_int("count") == 7
    assert section.get_int("native_int") == 3
    assert section.get_float("ratio") == 0.5
    assert section.get_bool("flag") is True
    assert section.get_bool("off") is False
    assert section.get_bool("native_bool") is True
    assert section.get_path("path") == Path("~/data").expanduser()
    assert section.get_choice("mode", {"fast", "safe"}) == "fast"
    assert section.get_secret_ref("password") == SecretRef("env", "DB_PASSWORD")
    assert section.get_int("absent", 5) == 5
    assert section.get_str("absent", None) is None

    with pytest.raises(ConfigurationError, match=r"capabilities\.demo\.absent: required key"):
        section.get_str("absent")
    with pytest.raises(ConfigurationError, match=r"capabilities\.demo\.text: expected an integer"):
        section.get_int("text")
    with pytest.raises(ConfigurationError, match="expected a number"):
        section.get_float("text")
    with pytest.raises(ConfigurationError, match="expected a boolean"):
        section.get_bool("text")
    with pytest.raises(ConfigurationError, match="expected one of: fast, safe"):
        section.get_choice("text", {"fast", "safe"})
    with pytest.raises(ConfigurationError, match="must be >= 10"):
        section.get_int("count", minimum=10)
    with pytest.raises(ConfigurationError, match=r"must be <= 0\.1"):
        section.get_float("ratio", maximum=0.1)
    with pytest.raises(ConfigurationError, match="expected a string"):
        section.get_str("native_int")
    with pytest.raises(ConfigurationError, match="expected an integer"):
        section.get_int("native_bool")


def test_literal_secrets_are_rejected_without_echoing_them() -> None:
    section = ConfigSection({"password": "hunter2-literal"}, "capabilities.db")
    with pytest.raises(ConfigurationError) as info:
        section.get_secret_ref("password")
    assert "hunter2" not in str(info.value)
    assert info.value.key == "capabilities.db.password"


def test_non_finite_numbers_are_rejected() -> None:
    section = ConfigSection({"x": "nan", "y": "inf"})
    for key in ("x", "y"):
        with pytest.raises(ConfigurationError, match="finite"):
            section.get_float(key)


def test_unknown_keys_are_rejected() -> None:
    with pytest.raises(ConfigurationError, match=r"runtime: unknown key\(s\): timout"):
        Configuration.from_mapping({"runtime": {"timout": 3}})
    with pytest.raises(ConfigurationError, match=r"<root>: unknown key\(s\): b"):
        ConfigSection({"a": 1, "b": 2}).check_keys({"a"})


def test_runtime_settings_validation() -> None:
    config = Configuration.from_mapping(
        {
            "runtime": {
                "name": "billing.v2",
                "workspace": "true",
                "workspace_root": "/tmp/x",
            }
        }
    )
    assert config.runtime.name == "billing.v2"
    assert config.runtime.workspace is True
    assert config.runtime.workspace_root == Path("/tmp/x")
    with pytest.raises(ConfigurationError, match=r"runtime\.name"):
        Configuration.from_mapping({"runtime": {"name": "has spaces"}})
    with pytest.raises(ConfigurationError, match=r"runtime\.timeout: must be greater than zero"):
        Configuration.from_mapping({"runtime": {"timeout": 0}})


def test_sections_are_immutable_and_reachable_by_path() -> None:
    config = Configuration.from_mapping(
        {
            "app": {"nested": {"items": [1, 2]}},
            "capabilities": {"sql": {"provider": "sqlite"}},
        }
    )
    nested = config.section("app.nested")
    assert nested["items"] == (1, 2)
    with pytest.raises(TypeError):
        nested._data["items"] = 3  # type: ignore[index]
    assert config.capability("sql").get_str("provider") == "sqlite"
    assert config.capability("missing") == {}
    assert config.capability("sql").path == "capabilities.sql"
    assert config.section("app").to_dict() == {"nested": {"items": [1, 2]}}
    assert "provider" not in repr(config)


def test_reserved_tables_must_be_tables() -> None:
    with pytest.raises(ConfigurationError, match="runtime: expected a table"):
        Configuration.from_mapping({"runtime": "fast"})
    with pytest.raises(ConfigurationError, match=r"capabilities\.sql: expected a table"):
        Configuration.from_mapping({"capabilities": {"sql": "sqlite"}})


def test_file_errors(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="configuration file not found"):
        Configuration.load(file=tmp_path / "missing.toml")
    bad = write(tmp_path / "bad.toml", "[runtime\nname = 1")
    with pytest.raises(ConfigurationError, match="invalid TOML"):
        Configuration.load(file=bad)


def test_table_and_value_conflicts_are_reported(tmp_path: Path) -> None:
    file = write(tmp_path / "c.toml", "[capabilities.sql]\nprovider = 'sqlite'\n")
    with pytest.raises(ConfigurationError, match=r"capabilities\.sql: a table and a value"):
        Configuration.load(file=file, overrides=[{"capabilities": {"sql": "x"}}])
    with pytest.raises(ConfigurationError, match="a value and a table"):
        Configuration.load(overrides=[{"app": 1}, {"app": {"x": 1}}])


def test_builder_reads_os_environ_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORCHESTRATOR_RUNTIME__NAME", "from-env")
    assert RuntimeBuilder().build().name == "from-env"
    assert RuntimeBuilder().with_environment(prefix=None).build().name == "orchestrator"
