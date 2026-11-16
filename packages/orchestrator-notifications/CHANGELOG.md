# Changelog — orchestrator-notifications

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/). Versionamento semântico; antes da 1.0, uma versão menor pode quebrar compatibilidade.

## [Não lançado]

Versão 0.1.0 preparada em 2026-11-15 na branch local `feature/notifications`, sem push, tag nem release. Depende do `orchestrator-core` 0.2.

### Adicionado

- `NotificationCapability`, `Notifier`, `Notification`, `Severity`, `DeliveryReport`, `DeliveryStatus`, `ChannelSettings` e o port `NotificationChannel` ([RFC-0007](../../docs/rfc/0007-capability-de-notificacoes.md), seções 2, 4 e 5).
- Estágios `NotifyStarted` e `NotifyOutcome`, `LifecycleNotice` e `default_formatter`, com textos formais em PT-BR (respostas 3 e 6).
- Política por canal (`required`, `attempts`, `delay`) e `required` por notificação em `send()` (resposta 5); sem limite de quantidade (resposta 4).
- Evento `NotificationFailed` e métrica `orchestrator.notifications.failed`.
- `orchestrator_notifications.testing`: `InMemoryChannel` e a suíte `NotificationChannelContract`.
