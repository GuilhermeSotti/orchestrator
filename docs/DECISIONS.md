# Registro de decisões — Orchestrator

| Campo | Valor |
|---|---|
| Atualizado em | 2026-11-12 |
| Situação | As 26 decisões levantadas pelas auditorias (D-00 a D-25) foram tomadas em 2026-11-12, por delegação explícita do responsável pelo projeto, e registradas em ADRs e RFCs |
| Análise original | Problema, alternativas e trade-offs de cada item: versão de 2026-11-11 deste documento, no histórico Git (`docs/OPEN_DECISIONS.md`) |

## 1. Decisões

| ID | Tema | Decisão | Registro | Em relação à recomendação de 2026-11-11 |
|---|---|---|---|---|
| D-00 | Destino do scaffold | Arquivar (tag `archive/scaffold-2026-07`) e reconstruir | [ADR-0002](adr/0002-destino-do-scaffold.md) | Igual |
| D-01 | Papel do repositório e localização do código | Incubação no repositório `orchestrator` durante a série 0.x; multirrepositório continua como alvo, com critérios de separação | [ADR-0001](adr/0001-topologia-de-repositorios.md) | **Diferente**: a recomendação era multirrepositório imediato com dois repositórios |
| D-02 | Forma da Public API | Biblioteca primeiro; sem spec nem CLI no Core | [ADR-0003](adr/0003-api-publica-biblioteca.md) | Igual |
| D-03 | Fronteiras e donos dos contratos | Core só com contratos transversais; cada Capability define seu port | [ADR-0004](adr/0004-fronteiras-core-capability-provider.md) | Igual |
| D-04 | Dependências do Core | Somente biblioteca padrão | [ADR-0005](adr/0005-dependencias-do-core.md) | **Diferente**: a recomendação era Pydantic como única dependência |
| D-05 | Síncrono ou assíncrono | Síncrono; sem runners de thread ou processo no Core | [ADR-0006](adr/0006-modelo-de-execucao-sincrono.md) | Igual |
| D-06 | Falha, teardown, cancelamento, timeout | Teardown sempre roda; erro primário preservado; cancelamento e prazo cooperativos | [RFC-0001](rfc/0001-ciclo-de-vida-da-execucao.md) | Igual, com teardown também quando cancelado antes do início |
| D-07 | Execution Context | Identidade imutável, `state` do consumidor, um contexto por execução | [RFC-0001](rfc/0001-ciclo-de-vida-da-execucao.md) | Igual |
| D-08 | Configuração e segredos | Padrões < TOML < ambiente < explícito; segredos por referência | [ADR-0007](adr/0007-configuracao-e-segredos.md) | Igual |
| D-09 | Dependency Injection | Construtor e `RuntimeBuilder`; sem contêiner | [ADR-0008](adr/0008-composicao-e-injecao-de-dependencias.md) | Igual |
| D-10 | Registry e plugins | Registro explícito; descoberta futura só por RFC com lista de permissão | [ADR-0009](adr/0009-registro-de-capabilities-e-compatibilidade.md) | Igual |
| D-11 | Compatibilidade entre pacotes | Faixas SemVer e verificação de `CORE_API_VERSION` no registro | [ADR-0009](adr/0009-registro-de-capabilities-e-compatibilidade.md) | Igual |
| D-12 | Retry | Utilitário explícito; sem retry por padrão | [ADR-0010](adr/0010-retry-explicito.md) | Igual |
| D-13 | Event Bus | Síncrono, em processo, falha de assinante isolada | [RFC-0001](rfc/0001-ciclo-de-vida-da-execucao.md), [ADR-0011](adr/0011-observabilidade.md) | Igual |
| D-14 | Logging, métricas, tracing | `logging` com correlação e mascaramento; port de métricas; tracing fora do MVP | [ADR-0011](adr/0011-observabilidade.md) | Igual |
| D-15 | Provision Dependencies | Verifica e abre Capabilities; nunca instala pacotes | [RFC-0001](rfc/0001-ciclo-de-vida-da-execucao.md) | Igual |
| D-16 | Persist Logs | Registro da execução para destinos registrados e descarga de logs; sem persistência de negócio | [RFC-0001](rfc/0001-ciclo-de-vida-da-execucao.md) | Igual; recursos passam a ser liberados no `finalize`, para o registro incluir erros de liberação |
| D-17 | Python e plataformas | `>=3.13`; CI com 3.13, 3.14 e 3.15 em Ubuntu e Windows | [ADR-0012](adr/0012-python-e-plataformas.md) | Igual |
| D-18 | Build e dependências de desenvolvimento | setuptools por pacote; ferramentas fixadas em `requirements/dev.txt`; lock com hashes pendente | [ADR-0013](adr/0013-build-e-ferramentas.md) | **Diferente**: a recomendação era grupos de dependência com lockfile do uv |
| D-19 | CI e controles do GitHub | Quatro jobs, ações fixadas por SHA, Dependabot; proteção de `main` documentada para o responsável aplicar | [ADR-0014](adr/0014-ci-e-controles-do-github.md) | Igual; com mantenedor único, PR obrigatório sem aprovação obrigatória |
| D-20 | MVP e publicação | Escopo da Fase 3; sem índice de pacotes; tags e artefatos em release do GitHub | [RFC-0002](rfc/0002-escopo-do-mvp-e-api-publica.md) | Igual |
| D-21 | Testes entre pacotes | `orchestrator_core.testing`, suíte de conformidade de Providers, exemplos instalados por wheel | [ADR-0015](adr/0015-testes-entre-pacotes.md) | Igual |
| D-22 | Itens futuros | Fora do escopo até a 1.0; RFC com caso de uso real | [ADR-0016](adr/0016-escopo-futuro.md) | Igual |
| D-23 | Titularidade, licença, nomes, idioma, visibilidade | MIT mantida; autoria genérica nos pacotes; documentação em português e código em inglês; titularidade jurídica e visibilidade ficam com o responsável | [ADR-0017](adr/0017-titularidade-licenca-idioma-visibilidade.md) | Parcial: dois itens não são decisões técnicas |
| D-24 | Commit, branch e merge | Conventional Commits, squash merge, `docs/*` e `chore/*`, tags por pacote | [ADR-0018](adr/0018-convencoes-de-commit-branch-e-versao.md) | Igual |
| D-25 | Convenções de fila no pacote SQL | Fora da plataforma; ficam com o consumidor | [ADR-0019](adr/0019-convencoes-de-fila-fora-da-plataforma.md) | Igual |

## 2. Pendências que dependem do responsável

Estas ações exigem acesso ou autoridade que o trabalho de 2026-11-12 não tinha:

1. Recuperar o acesso ao remoto e reconciliar o histórico ([guia](guides/recuperacao-do-historico.md)).
2. Aplicar a proteção de `main` e verificar os controles disponíveis no plano ([guia](guides/governanca-github.md)).
3. Habilitar o reporte privado de vulnerabilidades (canal citado em `SECURITY.md`).
4. Decidir a titularidade jurídica e a visibilidade do repositório (ADR-0017).
5. Remover do remoto as branches `feature`, `feature-core` e `teste` (ADR-0018).

## 3. Processo para novas decisões

- Decisão arquitetural: ADR em `docs/adr/`. Funcionalidade grande ou transversal: RFC em `docs/rfc/`, aceita antes da implementação.
- Decisões relacionadas podem dividir o mesmo registro.
- Toda escolha de tecnologia considera manutenção, adoção, segurança, licença e custo operacional.
