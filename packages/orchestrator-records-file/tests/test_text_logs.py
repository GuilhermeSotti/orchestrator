from __future__ import annotations

import logging
import os
import re
import time
from collections.abc import Iterator
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from orchestrator_core import ExecutionContext, RuntimeBuilder
from orchestrator_records_file import DEFAULT_LOG_PATH, TextLogHandler
from orchestrator_records_file._paths import host_and_user

SENTINEL = "S3NT1NEL-logs-77a0"
HOST, USER = host_and_user()


class _Sentinel:
    def resolve(self, target: str) -> str:
        return f"{SENTINEL}-{target}"


@pytest.fixture
def logger() -> Iterator[logging.Logger]:
    log = logging.getLogger("tests.records_file")
    log.setLevel(logging.INFO)
    log.propagate = False
    yield log
    for handler in list(log.handlers):
        log.removeHandler(handler)
        handler.close()


def _record(message: str, when: datetime, **attributes: str) -> logging.LogRecord:
    record = logging.LogRecord("tests.records_file", logging.INFO, __file__, 1, message, None, None)
    record.created = when.timestamp()
    for name, value in attributes.items():
        setattr(record, name, value)
    return record


def _file(day: datetime | date, *folders: str, pid: int | None = None) -> Path:
    name = f"{HOST}_{USER}_{os.getpid() if pid is None else pid}.txt"
    return Path(*folders, f"{day:%Y}", f"{day:%m}", f"{day:%d}", name)


def _touch(path: Path, text: str = "x\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_lines_follow_stage_step_and_date(tmp_path: Path, logger: logging.Logger) -> None:
    handler = TextLogHandler(tmp_path)
    logger.addHandler(handler)

    def automation(ctx: ExecutionContext) -> None:
        logger.info("before the step")
        with ctx.step("load"):
            logger.info("inside the step")

    result = RuntimeBuilder().with_environment({}, prefix=None).build().run(automation)
    assert result.succeeded
    handler.flush()
    day = result.record.started_at.astimezone(UTC)
    inside = (tmp_path / _file(day, "execute_automation", "load")).read_text("utf-8")
    outside = (tmp_path / _file(day, "execute_automation", "_")).read_text("utf-8")
    assert "inside the step" in inside
    assert "before the step" not in inside
    assert "before the step" in outside
    assert f"[{result.execution_id}|execute_automation] tests.records_file: inside" in inside
    assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}Z INFO ", inside)
    assert DEFAULT_LOG_PATH == "{stage}/{step}/{year}/{month}/{day}/{hostname}_{user}_{pid}.txt"


def test_secret_values_never_reach_the_files(tmp_path: Path, logger: logging.Logger) -> None:
    logger.addHandler(TextLogHandler(tmp_path))

    def automation(ctx: ExecutionContext) -> None:
        value = ctx.secrets.resolve("test:token").reveal()
        logger.info("calling the service with %s", value)
        msg = f"refused {value}"
        raise RuntimeError(msg)

    runtime = (
        RuntimeBuilder()
        .with_environment({}, prefix=None)
        .with_secret_resolver("test", _Sentinel())
        .build()
    )
    assert not runtime.run(automation).succeeded
    text = "".join(path.read_text("utf-8") for path in tmp_path.rglob("*.txt"))
    assert "calling the service with" in text
    assert SENTINEL not in text


@pytest.mark.parametrize(
    "template",
    [
        "",
        "/var/{year}/{month}/{day}.txt",
        "C:/logs/{year}/{month}/{day}.txt",
        "logs\\{year}/{month}/{day}.txt",
        "a//{year}/{month}/{day}.txt",
        "../{year}/{month}/{day}.txt",
        "./{year}/{month}/{day}.txt",
        "{unknown}/{year}/{month}/{day}.txt",
        "{year:04}/{month}/{day}.txt",
        "{year!r}/{month}/{day}.txt",
        "{}/{year}/{month}/{day}.txt",
        "a b/{year}/{month}/{day}.txt",
        "{stage}./{year}/{month}/{day}.txt",
        "{year}/{month}/{day}/{pid",
        "{stage}/{hostname}.txt",
    ],
)
def test_invalid_templates(tmp_path: Path, template: str) -> None:
    with pytest.raises(ValueError, match=r"path|placeholder|retention|template"):
        TextLogHandler(tmp_path, path=template)


def test_templates_without_dates_need_retention_disabled(tmp_path: Path) -> None:
    handler = TextLogHandler(tmp_path, path="{stage}/{hostname}.log", retention_months=None)
    record = _record("x", datetime(2026, 11, 15, tzinfo=UTC), stage="initialize")
    assert handler.path_for(record) == tmp_path.absolute() / "initialize" / f"{HOST}.log"
    with pytest.raises(ValueError, match="retention is disabled"):
        handler.purge()
    handler.close()


def test_values_never_leave_the_root(tmp_path: Path) -> None:
    handler = TextLogHandler(
        tmp_path,
        path="{automation}/{stage}/{step}/{execution_id}/{year}{month}{day}.txt",
        retention_months=None,
    )
    record = _record(
        "x",
        datetime(2026, 11, 15, 12, tzinfo=UTC),
        automation="../../etc",
        stage="aux",
        step="-",
        execution_id="",
    )
    path = handler.path_for(record)
    assert path.relative_to(tmp_path.absolute()).parts == (
        "_.._etc",
        "_aux",
        "_",
        "_",
        "20261115.txt",
    )
    handler.close()


def test_retention_removes_only_expired_files_of_the_template(tmp_path: Path) -> None:
    handler = TextLogHandler(tmp_path)  # 6 months: on 2026-11-15, files before 2026-05-15
    folders = ("execute_automation", "load")
    expired = [
        _touch(tmp_path / _file(date(2026, 4, 30), *folders, pid=1)),
        _touch(tmp_path / _file(date(2026, 5, 14), *folders, pid=1)),
        _touch(tmp_path / _file(date(2025, 12, 31), "initialize", "_", pid=7)),
    ]
    kept = [
        _touch(tmp_path / _file(date(2026, 5, 15), *folders, pid=1)),
        _touch(tmp_path / _file(date(2026, 11, 15), *folders, pid=1)),
        _touch(tmp_path / "execute_automation" / "load" / "2026" / "04" / "30" / "notes.md"),
        _touch(tmp_path / "execute_automation" / "load" / "2026" / "02" / "30" / "a_b_1.txt"),
        _touch(tmp_path / "backup" / "2020" / "01" / "01" / "a_b_1.txt"),
        _touch(tmp_path / "x" / "y" / "2020" / "01" / "01" / "a_b_1.txt.bak"),
    ]
    outside = _touch(tmp_path.parent / f"{tmp_path.name}-outside.txt")
    link = tmp_path / _file(date(2026, 4, 29), *folders, pid=2)
    link.parent.mkdir(parents=True)
    try:
        link.symlink_to(outside)
        linked = True
    except OSError:  # Windows without the privilege to create symbolic links
        linked = False
    assert handler.purge(date(2026, 11, 15)) == len(expired)
    assert not any(path.exists() for path in expired)
    assert all(path.exists() for path in kept)
    assert link.is_symlink() or not linked
    assert outside.exists()
    assert not (tmp_path / "execute_automation" / "load" / "2026" / "05" / "14").exists()
    assert not (tmp_path / "initialize").exists()
    assert (tmp_path / "execute_automation" / "load" / "2026" / "04" / "30").is_dir()
    handler.close()


def test_retention_runs_on_the_first_line_of_each_day(tmp_path: Path) -> None:
    handler = TextLogHandler(tmp_path, retention_months=1)
    old = tmp_path / _file(date(2026, 1, 1), "initialize", "_", pid=1)
    _touch(old)
    handler.handle(_record("first", datetime(2026, 11, 15, 8, tzinfo=UTC)))
    assert not old.exists()
    _touch(old)
    handler.handle(_record("second", datetime(2026, 11, 15, 9, tzinfo=UTC)))
    assert old.exists()
    handler.handle(_record("next day", datetime(2026, 11, 16, 0, 1, tzinfo=UTC)))
    assert not old.exists()
    handler.close()


def test_local_time_changes_folders_and_line_times(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if not hasattr(time, "tzset") or not Path("/usr/share/zoneinfo/America/Sao_Paulo").exists():
        pytest.skip("needs time.tzset and the system time zone database")
    monkeypatch.setenv("TZ", "America/Sao_Paulo")
    time.tzset()
    try:
        handler = TextLogHandler(tmp_path, utc=False)
        handler.handle(_record("late", datetime(2026, 11, 15, 1, 30, tzinfo=UTC)))
        handler.close()
        text = (tmp_path / _file(date(2026, 11, 14), "_", "_")).read_text("utf-8")
        assert text.startswith("2026-11-14 22:30:00,")
    finally:
        monkeypatch.delenv("TZ")
        time.tzset()


def test_errors_go_to_handle_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "logs"
    root.mkdir()
    handler = TextLogHandler(root)
    failures: list[logging.LogRecord] = []
    monkeypatch.setattr(handler, "handleError", failures.append)
    root.rmdir()
    root.write_text("a file where the folder was", encoding="utf-8")
    record = _record("lost", datetime(2026, 11, 15, tzinfo=UTC))
    handler.handle(record)
    assert failures == [record]
    handler.close()


def test_open_files_are_limited(tmp_path: Path) -> None:
    handler = TextLogHandler(tmp_path, max_open_files=2)
    when = datetime(2026, 11, 15, tzinfo=UTC)
    for step in ("a", "b", "c", "a"):
        handler.handle(_record(f"line {step}", when, stage="execute_automation", step=step))
    assert len(handler._streams) == 2
    handler.close()
    assert handler._streams == {}
    text = (tmp_path / _file(when, "execute_automation", "a")).read_text("utf-8")
    assert text.count("line a") == 2


def test_a_forked_process_writes_its_own_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    handler = TextLogHandler(tmp_path)
    when = datetime(2026, 11, 15, tzinfo=UTC)
    handler.handle(_record("parent", when))
    monkeypatch.setattr(os, "getpid", lambda: 999_999)
    handler.handle(_record("child", when))
    handler.close()
    child = (tmp_path / _file(when, "_", "_", pid=999_999)).read_text("utf-8")
    assert "child" in child
    assert "parent" not in child


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [({"retention_months": 0}, "retention_months"), ({"max_open_files": 0}, "max_open_files")],
)
def test_invalid_arguments(tmp_path: Path, kwargs: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        TextLogHandler(tmp_path, **kwargs)  # type: ignore[arg-type]


def test_root_must_exist(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="does not exist"):
        TextLogHandler(tmp_path / "missing")
