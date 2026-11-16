# Pacotes

Pacotes distribuíveis, incubados neste repositório durante a série 0.x ([ADR-0001](../docs/adr/0001-topologia-de-repositorios.md)). Cada pasta é autossuficiente: `pyproject.toml`, README, CHANGELOG, LICENSE, código em `src/` e testes em `tests/`.

| Pasta | Distribuição | Papel |
|---|---|---|
| [orchestrator-core](orchestrator-core) | `orchestrator-core` | Core: Runtime, pipeline, contexto, contratos |
| [orchestrator-sql](orchestrator-sql) | `orchestrator-sql` | Capability SQL |
| [orchestrator-sqlite](orchestrator-sqlite) | `orchestrator-sqlite` | Provider SQLite |
| [orchestrator-notifications](orchestrator-notifications) | `orchestrator-notifications` | Capability de notificações |
| [orchestrator-notifications-smtp](orchestrator-notifications-smtp) | `orchestrator-notifications-smtp` | Provider de e-mail (SMTP) |
| [orchestrator-notifications-teams](orchestrator-notifications-teams) | `orchestrator-notifications-teams` | Provider de Microsoft Teams |
| [orchestrator-records-file](orchestrator-records-file) | `orchestrator-records-file` | Registros e logs em arquivo |
| [orchestrator-calendar](orchestrator-calendar) | `orchestrator-calendar` | Capability de calendários |

Compatibilidade entre versões: [docs/COMPATIBILITY.md](../docs/COMPATIBILITY.md).
