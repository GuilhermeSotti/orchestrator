from __future__ import annotations

import json
from pathlib import Path
from typing import ClassVar

import pytest

from batch_check import Parameters, check_batch
from batch_check.__main__ import build_runtime, cancel_on_signals, main, restore_signals
from orchestrator_core import CancellationToken, ConfigSection, SecretStore
from orchestrator_notifications import Notification
from orchestrator_notifications.testing import InMemoryChannel

DATA = Path(__file__).resolve().parents[1] / "data"
CONFIG = Path(__file__).resolve().parents[1] / "orchestrator.toml"


class Recording(InMemoryChannel):
    """Stands in for the SMTP channel of the example configuration."""

    sent_all: ClassVar[list[Notification]] = []

    @classmethod
    def from_config(cls, section: ConfigSection) -> Recording:
        return cls()

    def send(self, notification: Notification, secrets: SecretStore) -> None:
        super().send(notification, secrets)
        Recording.sent_all.append(notification)


@pytest.fixture(autouse=True)
def _clear() -> None:
    Recording.sent_all.clear()


def _run(folder: Path) -> object:
    runtime = build_runtime(str(CONFIG), {"smtp": Recording})
    return runtime.run(
        check_batch,
        name="batch-check",
        parameters={"input_dir": str(folder)},
        parameters_validator=Parameters.validate,
    )


def test_success_sends_the_summary_and_the_outcome_notice() -> None:
    result = _run(DATA)
    assert result.succeeded, result.error  # type: ignore[attr-defined]
    assert result.output == {"files": 2, "records": 3}  # type: ignore[attr-defined]
    kinds = [n.kind for n in Recording.sent_all]
    assert kinds == ["batch.checked", "execution.succeeded"]
    assert Recording.sent_all[1].subject == "[batch-check] Execução concluída com sucesso"


def test_an_empty_batch_file_fails_and_sends_the_failure_notice(tmp_path: Path) -> None:
    (tmp_path / "vazio.txt").write_text("pedido;valor\n", encoding="utf-8")
    result = _run(tmp_path)
    assert result.status.value == "failed"  # type: ignore[attr-defined]
    (notice,) = Recording.sent_all
    assert notice.kind == "execution.failed"
    facts = dict(notice.facts)
    assert facts["Erro"] == "ValueError: batch files without records: vazio.txt"
    assert [step.name for step in result.steps] == ["check_file"]  # type: ignore[attr-defined]


def test_command_line_without_notification_channels(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config = tmp_path / "quiet.toml"
    config.write_text("[app]\n", encoding="utf-8")
    assert main([str(DATA), "--config", str(config)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["record"]["status"] == "succeeded"
    assert payload["output"] == {"files": 2, "records": 3}
    assert main([str(tmp_path / "absent"), "--config", str(config)]) == 1


def test_termination_signals_cancel_the_run_and_handlers_are_restored() -> None:
    import signal

    before = signal.getsignal(signal.SIGTERM)
    token = CancellationToken()
    previous = cancel_on_signals(token)
    try:
        handler = signal.getsignal(signal.SIGTERM)
        assert callable(handler)
        handler(signal.SIGTERM, None)
        assert token.reason == "SIGTERM"
    finally:
        restore_signals(previous)
    assert signal.getsignal(signal.SIGTERM) == before
