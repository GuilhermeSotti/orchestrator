# Orchestrator

Plataforma modular de automação em Python. Padroniza o ciclo de vida das automações — preparação, execução, finalização, logs, métricas, retry, cancelamento — para que cada projeto consumidor escreva apenas a sua lógica de negócio.

## Situação

| Item | Valor |
|---|---|
| Fase | Incubação, série 0.x ([roadmap](docs/IMPLEMENTATION_ROADMAP.md)) |
| Versões | `orchestrator-core` 0.1.0, `orchestrator-sql` 0.1.0, `orchestrator-sqlite` 0.1.0 |
| Python | 3.13 ou superior |
| Publicação | Nenhuma em índice de pacotes; instalação a partir do repositório |
| Decisões | Todas registradas em [docs/DECISIONS.md](docs/DECISIONS.md) |

## Pacotes

| Pacote | Papel | Dependências |
|---|---|---|
| [`orchestrator-core`](packages/orchestrator-core) | Runtime, Execution Pipeline de oito estágios, Execution Context, contratos de Capability e Provider | Só a biblioteca padrão |
| [`orchestrator-sql`](packages/orchestrator-sql) | Capability SQL: consultas parametrizadas, transações, identificadores validados | `orchestrator-core` |
| [`orchestrator-sqlite`](packages/orchestrator-sqlite) | Provider SQLite para a Capability SQL | `orchestrator-sql` |
| [`orchestrator-notifications`](packages/orchestrator-notifications) | Capability de notificações: canais, avisos de ciclo de vida, política de falha | `orchestrator-core` |
| [`orchestrator-notifications-smtp`](packages/orchestrator-notifications-smtp) | Provider de e-mail (SMTP) para as notificações, só com a biblioteca padrão | `orchestrator-notifications` |
| [`orchestrator-notifications-teams`](packages/orchestrator-notifications-teams) | Provider de Microsoft Teams (webhook de Workflows) para as notificações | `orchestrator-notifications` |
| [`orchestrator-records-file`](packages/orchestrator-records-file) | Registros de execução em JSON Lines e logs técnicos em TXT, com retenção e vários processos por pasta | `orchestrator-core` |
| [`orchestrator-calendar`](packages/orchestrator-calendar) | Capability de calendários de dias úteis, com feriados mantidos manualmente em arquivos | `orchestrator-core` |

Os pacotes incubam neste repositório e cada um pode ser separado em repositório próprio ([ADR-0001](docs/adr/0001-topologia-de-repositorios.md)).

## Exemplo

```python
from orchestrator_core import ExecutionContext, RuntimeBuilder


def conciliar(ctx: ExecutionContext) -> int:
    ctx.logger.info("conciliando %s", ctx.parameters["dia"])
    return 42


runtime = RuntimeBuilder().with_config_file("orchestrator.toml").build()
result = runtime.run(conciliar, parameters={"dia": "2026-11-12"})
result.raise_for_status()
```

Projetos completos: [`examples/hello-automation`](examples/hello-automation) e [`examples/sales-report`](examples/sales-report). Guia: [primeiros passos](docs/guides/primeiros-passos.md).

## Desenvolvimento

```powershell
py -3.13 -m venv .venv
.venv\Scripts\python -m pip install -r requirements\dev.txt
.venv\Scripts\python -m pip install -e packages\orchestrator-core -e packages\orchestrator-sql -e packages\orchestrator-sqlite -e packages\orchestrator-notifications -e packages\orchestrator-notifications-smtp -e packages\orchestrator-notifications-teams -e packages\orchestrator-records-file -e packages\orchestrator-calendar -e examples\hello-automation -e examples\sales-report -e examples\batch-check

ruff check .
ruff format --check .
mypy
pytest
python tools\build_packages.py --check
python -m tools.e2e
```

Regras de contribuição: [CONTRIBUTING.md](CONTRIBUTING.md). Governança: [GOVERNANCE.md](GOVERNANCE.md). Segurança: [SECURITY.md](SECURITY.md).

## Estrutura

```text
orchestrator/
├── packages/            pacotes distribuíveis (um por pasta, cada um com pyproject, README, CHANGELOG, testes)
├── examples/            projetos consumidores de exemplo, instalados a partir dos pacotes
├── docs/                decisões (ADR, RFC), guias, roadmap, compatibilidade, auditorias
├── tools/               verificações do repositório (links, fronteiras, build reproduzível)
├── requirements/        versões das ferramentas de desenvolvimento
├── .github/             CI, release, Dependabot, templates de issue e PR
├── ARCHITECTURE.md      arquitetura e regras de dependência
├── GOVERNANCE.md        processo de engenharia
├── SECURITY.md          política de segurança
├── CONTRIBUTING.md      como contribuir
├── ROADMAP.md           resumo do roadmap
└── CHANGELOG.md         mudanças do repositório (cada pacote tem o seu)
```

## Licença

MIT. Veja [LICENSE](LICENSE).
