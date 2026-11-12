# RFC-0002 — Escopo do MVP, API pública e distribuição

| Campo | Valor |
|---|---|
| Status | Aceita e implementada em `orchestrator-core` 0.1.0 |
| Data | 2026-11-12 |
| Decisão | D-20 |
| Decisor | Claude, por delegação explícita do responsável pelo projeto (2026-11-12) |

## 1. Escopo da 0.1.0

Incluído: Runtime com os oito estágios; Execution Context; configuração com precedência; segredos por referência; contrato e registro de Capabilities; teardown garantido; logging com correlação e mascaramento; eventos; port de métricas; retry explícito; cancelamento e prazo cooperativos; módulo de apoio a testes; dois projetos consumidores de exemplo.

Excluído: Runtime assíncrono; descoberta automática de plugins; interpretador de spec e CLI genérica; persistência de histórico; integração com OpenTelemetry; itens da ADR-0016.

## 2. API pública

Somente estes nomes são públicos; um teste falha se a lista mudar sem atualização desta RFC.

**`orchestrator_core`**

- Runtime: `Runtime`, `RuntimeBuilder`, `Automation`.
- Execução: `ExecutionContext`, `ExecutionResult`, `ExecutionRecord`, `ExecutionOutcome`, `ExecutionStatus`, `StageOutcome`, `StageRecord`, `StageStatus`, `ErrorInfo`, `Finalizer`, `ResourceScope`.
- Pipeline: `Stage`, `FunctionStage`, `Phase`.
- Capabilities: `Capability`.
- Configuração e segredos: `Configuration`, `ConfigSection`, `RuntimeSettings`, `Secret`, `SecretRef`, `SecretResolver`, `SecretStore`.
- Controle: `CancellationToken`, `RetryPolicy`, `RetryAttempt`, `retry`, `is_retryable`.
- Eventos: `Event`, `EventHandler`, `ExecutionStarted`, `ExecutionFinished`, `StageStarted`, `StageFinished`.
- Ports: `MetricsRecorder`, `ExecutionRecordSink`, `Clock`.
- Erros: `OrchestratorError`, `ConfigurationError`, `PipelineDefinitionError`, `CapabilityError`, `CapabilityNotFoundError`, `DuplicateCapabilityError`, `IncompatibleCapabilityError`, `CapabilityUnavailableError`, `ProviderError`, `SecretResolutionError`, `ExecutionInterruptedError`, `ExecutionCancelledError`, `ExecutionTimeoutError`, `ExecutionFailedError`.
- Versões: `__version__`, `CORE_API_VERSION`.

**`orchestrator_core.logs`**: `configure_logging`, `ExecutionContextFilter`, `RedactingFilter`, `JsonFormatter`, `TEXT_FORMAT`.

**`orchestrator_core.testing`**: `FakeClock`, `InMemoryMetrics`, `EventRecorder`, `InMemoryRecordSink`, `check_capability_conformance`.

Todo nome público tem docstring; a maioria tem exemplo executado como doctest.

## 3. Critérios de aceite e situação

| # | Critério | Situação em 2026-11-12 |
|---:|---|---|
| 1 | Wheel instala em ambiente limpo, Windows e Linux, nas versões suportadas | Verificado em Linux, Python 3.13. Windows, 3.14 e 3.15: primeira execução da CI |
| 2 | Exemplo executa de ponta a ponta só com a API pública | Verificado, instalado a partir dos wheels |
| 3 | Dependências de execução do Core exatamente as aprovadas (nenhuma) | Verificado por teste |
| 4 | Falha em qualquer estágio: teardown executa e o erro original é preservado | Verificado (matriz de falha) |
| 5 | Execuções sequenciais e paralelas sem compartilhar estado nem recursos | Verificado (600 execuções, 8 threads) |
| 6 | Nenhum segredo em logs ou eventos | Verificado (valor-sentinela) |
| 7 | Ruff, formatação, MyPy estrito e Pytest; cobertura mínima | Verificado localmente; meta de cobertura: 90% de linhas e ramos, aplicada pela CI |
| 8 | Documentação de API, README, CHANGELOG e ADRs | Verificado |

## 4. Distribuição

1. Nenhum índice de pacotes na 0.1.0. Cada release é uma tag `<distribuição>/v<versão>`; o workflow de release anexa wheel e sdist a uma release do GitHub.
2. Instalação a partir do repositório: `pip install "orchestrator-core @ git+https://github.com/<dono>/orchestrator@orchestrator-core/v0.1.0#subdirectory=packages/orchestrator-core"`.
3. Publicar no PyPI ou num índice privado exige nova RFC e autorização do responsável. Antes disso, verificar se os nomes `orchestrator-core`, `orchestrator-sql` e `orchestrator-sqlite` estão livres no índice escolhido.
