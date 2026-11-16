"""Default texts of the lifecycle notifications, in Brazilian Portuguese.

RFC-0007, answer 3: the automatic messages of the platform are formal and in
PT-BR by default. They are content for people, not log or exception messages,
which stay in English (ADR-0017). A consumer replaces them by registering the
Capability with ``formatter=``.
"""

from __future__ import annotations

from datetime import UTC, datetime

from orchestrator_notifications._model import LifecycleNotice, Notification, Severity

_TITLES = {
    "started": "Execução iniciada",
    "succeeded": "Execução concluída com sucesso",
    "failed": "Execução concluída com falha",
    "cancelled": "Execução cancelada",
    "timed_out": "Execução interrompida por tempo limite",
}
_SENTENCES = {
    "started": "Informamos que a execução da automação {automation} foi iniciada.",
    "succeeded": "Informamos que a execução da automação {automation} foi concluída com sucesso.",
    "failed": "Informamos que a execução da automação {automation} foi concluída com falha.",
    "cancelled": "Informamos que a execução da automação {automation} foi cancelada.",
    "timed_out": (
        "Informamos que a execução da automação {automation} foi interrompida "
        "por exceder o tempo limite."
    ),
}
_SEVERITIES = {
    "started": Severity.INFO,
    "succeeded": Severity.INFO,
    "failed": Severity.ERROR,
    "cancelled": Severity.WARNING,
    "timed_out": Severity.ERROR,
}
_FOOTER = "Mensagem automática da plataforma Orchestrator."


def default_formatter(notice: LifecycleNotice) -> Notification:
    """Build the formal PT-BR notification of ``notice``.

    Content: automation, Runtime, execution, start, duration and, on failure,
    the masked error. Never parameters, results, configuration or tracebacks.

    Example:
        >>> from datetime import datetime, UTC
        >>> notice = LifecycleNotice(
        ...     status="succeeded",
        ...     automation="faturamento",
        ...     runtime="default",
        ...     execution_id="abc",
        ...     started_at=datetime(2026, 11, 15, 12, tzinfo=UTC),
        ...     duration=3.21,
        ... )
        >>> default_formatter(notice).subject
        '[faturamento] Execução concluída com sucesso'
    """
    facts = [
        ("Automação", notice.automation),
        ("Runtime", notice.runtime),
        ("Execução", notice.execution_id),
        ("Início", _utc(notice.started_at)),
    ]
    if notice.duration is not None:
        facts.append(("Duração", f"{notice.duration:.1f} s"))
    if notice.error is not None:
        facts.append(("Erro", f"{notice.error.type}: {notice.error.message}"))
    body = f"{_SENTENCES[notice.status].format(automation=notice.automation)}\n\n{_FOOTER}"
    kind = f"execution.{notice.status}"
    return Notification(
        subject=f"[{notice.automation}] {_TITLES[notice.status]}",
        body=body,
        severity=_SEVERITIES[notice.status],
        facts=tuple(facts),
        kind=kind,
        dedup_key=f"{notice.execution_id}:{kind}",
    )


def _utc(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
