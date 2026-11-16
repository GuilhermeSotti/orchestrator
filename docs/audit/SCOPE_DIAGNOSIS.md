# Diagnóstico de escopo — controles reutilizáveis de automação

| Campo | Valor |
|---|---|
| Data | 2026-11-14 |
| Pedido | Nove itens de escopo apresentados pelo responsável em 2026-11-13: ciclo de vida e finalização, fluxo e subetapas, fila, notificações, logs e registros, mapeamentos compartilhados, fluxos de login, segredos e calendários |
| Base analisada | `main` em `e8eaabe`, igual a `origin/main`; 159 arquivos versionados, sem alterações locais antes destes documentos |
| Natureza | Diagnóstico: só fatos. As propostas estão nas RFCs [0004](../rfc/0004-controles-reutilizaveis-escopo-e-sequencia.md) a [0012](../rfc/0012-autenticacao-por-sistema.md), nenhuma aceita |
| Autor | Claude, a pedido do responsável |

Classificação usada: **verificado** (código lido ou comando executado nesta data), **documentado** (consta de ADR ou RFC aceita), **inferido** e **pendente** (depende de informação ou decisão do responsável).

## 1. Como foi verificado

O repositório foi copiado da pasta do responsável em 2026-11-13 e analisado em Linux, Python 3.13.18, com as versões de `requirements/dev.txt` (Ruff 0.16.9, MyPy 2.3.1, Pytest 9.1.1, setuptools 84.0.0). Em 2026-11-14 a pasta foi listada de novo: só metadados do Git tinham mudado (uma busca no remoto e uma configuração do editor). Nada foi alterado na pasta durante a verificação.

Comandos executados na cópia, com estes documentos já incluídos:

| Comando | Resultado |
|---|---|
| `git status --porcelain -b`, antes destes documentos | `## main...origin/main`, sem alterações |
| `ruff check .` | `All checks passed!` |
| `ruff format --check .` | `135 files already formatted`. O Ruff também formata os blocos de código Python dos arquivos Markdown: um exemplo longo numa RFC chegou a falhar e foi corrigido |
| `mypy` | `Success: no issues found in 48 source files` |
| `pytest` | `214 passed, 1 skipped` |
| `python tools/check_docs.py` | código de saída 0 |
| `python -m pytest tools` | `14 passed` |
| `python tools/build_packages.py --check` | `reproducible: 6 artifacts` |
| `python -m tools.e2e` | `e2e ok` |

Não verificado:

- cobertura mínima de 90%: o coverage.py não estava disponível no ambiente e não podia ser instalado;
- Windows, Python 3.14 e 3.15, e a execução da CI no GitHub;
- nenhuma revisão independente: a pasta `ai-harness` existe ao lado do repositório, mas não havia integração executável nesta sessão (nenhum servidor MCP local e nenhum shell na máquina do responsável).

Experimentos feitos em 2026-11-13 com scripts descartáveis, fora do repositório, contra o código real:

| ID | O que foi feito | Observado |
|---|---|---|
| EX1 | Automação em espera recebe `SIGTERM`, sem tratamento de sinal | Processo encerrado com código −15; o finalizer não executou |
| EX2 | Igual, com o sinal ligado ao `CancellationToken` e espera por `ctx.sleep` | Status `cancelled`; o finalizer executou |
| EX3 | Estágio de teardown inserido depois de `finalize` | O handle da Capability ainda é alcançável (recursos já liberados) e `ctx.outcome` já reflete o erro ocorrido em `finalize` |
| EX4 | Automação termina bem e um finalizer lança erro | Status final `failed`; `ExecutionFinished` publicado depois de todo o pipeline, com `ErrorInfo` mascarado |
| EX5 | Capability que usa, em `open(ctx)`, o handle de outra | Funciona se registrada depois da outra; registrada antes, falha com `CapabilityError: capability 'queue_db' has not been provisioned yet`. Duas `SqlCapability` com nomes diferentes dão sessões distintas |
| EX6 | Automação resolve um segredo e lança erro com o valor na mensagem | O finalizer recebe o texto com o segredo (`str(outcome.error)`); o registro traz `***`. Nenhum nome público do Core mascara texto arbitrário |
| EX7 | `ctx.retry` e `ctx.sleep` chamados num finalizer depois de prazo estourado ou cancelamento | Lançam `ExecutionTimeoutError` ou `ExecutionCancelledError` na hora, com zero tentativas. Depois de falha comum funcionam. A função de módulo `retry()` funciona nos três casos |
| EX8 | Segredo composto (`Server=…;Password=…`) resolvido; só a parte da senha vai para o log | O valor inteiro é mascarado; a parte derivada aparece em claro |
| EX9 | Referência com esquema desconhecido (`senha:abc123`) | A mensagem de erro repete o esquema (`'senha'`), não o restante |

## 2. Estado do repositório em relação à documentação

| Divergência | Evidência | Situação |
|---|---|---|
| `docs/DECISIONS.md` (seção 2, item 1) e o roadmap (E0.4, E1.5, seção 11) tratam o remoto como inacessível e o histórico como não reconciliado | O reflog local registra, em 2026-11-13, um push que deixou `origin/main` em `e8eaabe`, o mesmo commit de `main`. A busca mais recente trouxe duas branches do Dependabot (Actions e `requirements/dev.txt`) | Verificado nas referências locais. A documentação ficou para trás. O valor anterior de `origin/main` não está na cópia local, então não dá para saber, daqui, se a reconciliação com `merge -s ours` do [guia](../guides/recuperacao-do-historico.md) foi feita ou se o histórico remoto de julho foi substituído. Cabe ao responsável confirmar no GitHub e atualizar os documentos |
| Primeira execução da CI "ainda não aconteceu" (roadmap, E1.5) | Não consultado | Pendente: não verificado nesta sessão |
| Ambiente virtual da pasta | `.venv/pyvenv.cfg`: Python 3.11.9, criado sob outro perfil de usuário | Verificado. Não serve aos pacotes, que exigem Python 3.13 ou superior; recriar o ambiente continua pendente (roadmap, E1.2) |

## 3. Diagnóstico por item

### 3.1 Ciclo de vida e finalização de processos

**Existe (verificado).**

| Mecanismo | Onde | Testes |
|---|---|---|
| Pipeline de oito estágios; o teardown (`finalize`, `persist_logs`, `shutdown`) sempre roda; erro primário preservado; erros de teardown agregados | `_runtime.py` (`Runtime._execute`), `_stages.py`; RFC-0001, seção 3 | `test_pipeline.py::test_failure_matrix`, `test_teardown_errors_are_aggregated_and_do_not_mask_the_primary_error`, `test_keyboard_interrupt_runs_teardown_then_propagates` |
| Recursos liberados em ordem inversa; finalizers com o desfecho provisório | `ResourceScope`, `ExecutionContext.add_finalizer` | `test_finalizers_see_the_success_outcome_and_run_before_resources`, `test_resource_scope_releases_in_reverse_order_and_collects_errors`, `test_provisioning_failure_releases_what_was_acquired` |
| Cancelamento cooperativo e prazo | `CancellationToken`, `run(timeout=...)`, `ctx.check()`, `ctx.sleep()`, `ctx.remaining()` | `test_retry_and_interruptions.py` (cancelamento antes do início e de outra thread, prazo em esperas e antes de cada estágio) |
| Isolamento entre execuções | Um contexto, um escopo de recursos e um handle por execução | `test_concurrency.py::test_stress_sequential_and_parallel_executions_are_isolated` |

**Lacunas concretas.**

| ID | Lacuna | Evidência |
|---|---|---|
| L1.1 | Sinais de término não chegam ao `CancellationToken`. Com a disposição padrão, `SIGTERM` encerra o processo sem teardown. Nenhum código, exemplo ou guia do repositório faz a ligação. Em Windows, um encerramento por `TerminateProcess` não pode ser interceptado por nenhum programa | EX1, EX2; busca por `signal` no repositório sem resultados |
| L1.2 | Não há espera nem retry utilizáveis no teardown depois de prazo ou cancelamento: `ctx.retry` e `ctx.sleep` verificam `ctx.check()` e lançam na hora. Também não existe prazo próprio para o teardown | EX7; `_context.py` (`sleep`, `retry`) |
| L1.3 | O prazo não interrompe código que não coopera; interrupção forçada está fora do Core | Documentado: RFC-0001, seção 5; ADR-0006; `test_overrunning_automation_succeeds_with_a_warning` |
| L1.4 | "Finalização de processos" pode significar encerrar processos do sistema operacional abertos pela automação. Nada existe para isso | Pendente: depende de esclarecimento do responsável |

Não é lacuna: um escopo de limpeza por parte da automação já é possível com `ResourceScope()`, que é público.

### 3.2 Fluxo e subetapas

**Existe (verificado).** Desfecho, eventos e métrica por **estágio do pipeline** (`StageOutcome`, `StageRecord`, `StageStarted`, `StageFinished`, `orchestrator.stage.duration_seconds`); estágios customizados (`with_stage`); eventos próprios do consumidor (`ctx.publish`); `ctx.state`. Testes: `test_custom_stages_can_be_inserted_without_changing_the_builtin_ones`, `test_lifecycle_events_are_published_in_order`, `test_custom_events_can_be_published`.

**Falta.** Subetapa **dentro** da automação: nome, status, duração e erro de cada parte, campo de correlação nos logs e presença no registro da execução. Hoje o consumidor só consegue isso com eventos próprios, e o resultado não entra no `ExecutionRecord`, que é montado apenas pelo Runtime.

**Limites documentados.** Workflow engine, checkpoint, retomada, pausa e execução parcial estão fora do escopo até a 1.0 e não podem aumentar o Core (ADR-0016; RFC-0001, seção 10). Uma camada declarativa só pode surgir como pacote separado, por RFC (ADR-0003).

### 3.3 Fila

**Existe.** Nada implementado. A ADR-0019 mantém as convenções de fila do scaffold fora da plataforma e exige RFC própria para uma Capability de fila genérica. `ARCHITECTURE.md` lista Queue entre as Capabilities previstas.

**Pré-requisitos ausentes para um Provider de fila sobre SQL (verificado).**

- `SqlSession` não limita linhas nem lê em partes: só há `fetch_all` e `select` sem limite (`_session.py`).
- `SqlProvider.connect()` não recebe contexto nem segredos (ver 3.8, L8.2).
- Só existe o Provider SQLite; o segundo Provider foi adiado (roadmap, E4.4).

**Disponível e útil (verificado).** A mesma Capability pode ser registrada duas vezes com nomes diferentes, e uma Capability pode usar o handle de outra em `open(ctx)`, se registrada depois (EX5; `test_capabilities_are_provisioned_in_registration_order`).

### 3.4 Notificações

**Existe.** Nenhuma Capability de notificação. Pontos de extensão: eventos (`on_event`), estágios customizados, finalizers e handles de Capability. O guia de Capabilities usa um `Notifier` hipotético apenas como ilustração.

**Fatos que condicionam o desenho (verificados).**

- Um assinante de evento que falha é registrado em log e contado em `orchestrator.event_handler.errors`; o resultado da execução não muda (`test_failing_handlers_are_isolated`).
- `ExecutionFinished` é publicado depois do `shutdown`. O assinante recebe só o evento: não há contexto, handles nem `ctx.secrets` (EX4; `_runtime.py`, `Runtime._report`).
- Um finalizer ou estágio de teardown que lança erro transforma uma execução bem-sucedida em `failed` (EX4; RFC-0001, seção 3).
- Os finalizers recebem o desfecho calculado antes do estágio `finalize`; um estágio inserido depois de `finalize` já enxerga os erros desse estágio (EX3).
- O texto do erro chega sem máscara a finalizers e estágios, e não há API pública para mascarar texto fora do `logging` (EX6). Uma mensagem montada a partir de `str(outcome.error)` pode levar um segredo.
- A lacuna L1.2 atinge justamente os avisos de `timed_out` e `cancelled`.

### 3.5 Logs e registros

**Existe (verificado).**

| Mecanismo | Onde | Testes |
|---|---|---|
| Logging técnico pela biblioteca padrão, com correlação (`execution_id`, `automation`, `stage`), mascaramento e saída JSON | `orchestrator_core.logs` | `test_observability.py` (cinco testes de log) |
| Registro mascarado da execução e port de destino | `ExecutionRecord`, `ExecutionRecordSink`, `with_record_sink` | `test_record_sinks_receive_the_record_and_their_failures_are_reported`, `test_sentinel_secret_never_reaches_logs_events_records_or_repr` |

**Falta.**

- Destino em arquivo para os logs: `configure_logging` só instala um handler de stream. O consumidor consegue hoje montar um `FileHandler` e adicionar os dois filtros à mão; não há guia nem exemplo.
- Nenhum destino de registro distribuído: só existe o `InMemoryRecordSink`, para testes.

**Restrição de desenho (verificado).** Os destinos são chamados em `persist_logs`, depois que `finalize` liberou os recursos, e `write(record)` não recebe o contexto. Um destino SQL não pode usar a sessão da execução nem `ctx.secrets`: precisa de conexão e credenciais próprias.

**Por decisão.** O Core não persiste dados de negócio; histórico em banco é papel de uma Capability futura (RFC-0001, seção 9; D-16). Logs de negócio e auditoria pertencem ao consumidor. O `ExecutionRecord` não carrega parâmetros nem o retorno da automação.

### 3.6 Repositório compartilhado de mapeamentos

**Existe.** Nada. O que há de próximo são as tabelas do consumidor na configuração (`ctx.config.section("app")`): servem a poucos valores estáticos de um projeto, não a um repositório compartilhado, versionado e validado.

**Atenção.** Excel é Capability prevista e não implementada. Ler Excel exige a primeira dependência de terceiros em tempo de execução da plataforma (seção 4).

### 3.7 Fluxos de login por sistema

**Existe.** Nada. Também não há Capability de navegador, HTTP ou desktop em que um fluxo pudesse rodar. Aplicam-se os mecanismos gerais: segredos por referência, `ctx.resources` para garantir logout e `ctx.retry`.

### 3.8 Credenciais e segredos

**Existe (verificado).** `SecretRef`, port `SecretResolver`, `SecretStore` por execução, esquemas `env:` e `file:`, `with_secret_resolver`, `Secret` (sem `repr`, sem serialização, comparação em tempo constante), recusa de literal sem eco e mascaramento em logs (com os filtros), eventos e registros. Testes: `test_secrets.py` (seis testes, incluindo o do valor-sentinela) e `test_literal_secrets_are_rejected_without_echoing_them`.

**Lacunas concretas.**

| ID | Lacuna | Evidência |
|---|---|---|
| L8.1 | Nenhum Provider de cofre | Só `EnvSecretResolver` e `FileSecretResolver` em `_secrets.py` |
| L8.2 | O port SQL não tem caminho para credenciais: `SqlProvider.from_config(section)` e `connect()` não recebem contexto nem `SecretStore`. Um Provider com senha teria de ler o ambiente por conta própria, fora do mascaramento. O SQLite não tem credenciais, por isso a lacuna não apareceu | `orchestrator_sql/_provider.py`, `_capability.py` (`open`) |
| L8.3 | Não há segredos fora de uma execução: o `SecretStore` é criado dentro de `run()` e o `Redactor` não é público. Destinos de registro e assinantes de eventos não conseguem resolver referências | `_runtime.py`, `__init__.py` |
| L8.4 | Mascarar texto só é possível pelos filtros de logging; `ErrorInfo.from_exception` exige um `Redactor`, que não é público | EX6 |
| L8.5 | Só o valor exato resolvido é mascarado. Partes de um segredo composto (cadeia de conexão, JSON) aparecem em claro | EX8 |
| L8.6 | Sem cache: cada `resolve` chama o resolvedor. Com cofre remoto, latência e limites de taxa ficam por conta do Provider | `_secrets.py` (`SecretStore.resolve`) |

Limites já documentados na ADR-0007: valores com menos de 4 caracteres não são mascarados; `result.error` e `result.output` não são mascarados. Observação menor: a mensagem de esquema desconhecido repete o esquema (EX9).

### 3.9 Calendários, feriados e dias úteis

**Existe.** Nada. A biblioteca padrão não traz dados de feriados. `ctx.now()` devolve UTC e o Core não tem conceito de fuso do negócio; em Windows, o módulo `zoneinfo` depende do pacote `tzdata`, que é de terceiros. Agendamento está fora do escopo (ADR-0016): calendários, aqui, servem a cálculos dentro da automação.

## 4. Decisões vigentes que os itens tocam

| Decisão | Item | Situação | O que cabe ao responsável |
|---|---|---|---|
| ADR-0016; RFC-0001, seção 10 | 2 | Rastrear subetapas não está na lista de exclusões, mas é vizinho de workflow engine e de execução parcial. Composição declarativa está bloqueada (ADR-0003) | Confirmar a fronteira antes de qualquer mudança no Core |
| ADR-0019 | 3 | Sem conflito se a Capability for genérica; a RFC própria exigida é a 0008. As convenções do consumidor continuam fora | Aceitar ou não a RFC-0008 |
| ADR-0004 | 3, 5, 6, 9 | A regra Provider → Capability → Core não prevê um Provider que use outra Capability como infraestrutura (fila sobre SQL, por exemplo) | Registrar a regra em ADR |
| ADR-0006 | 1 | Interrupção forçada e supervisão por processo estão fora do Core | Só reabrir com caso real (L1.3) |
| ADR-0009, item 5; `COMPATIBILITY.md` | todos os que mudam o Core | Antes da 1.0, a versão de API precisa ser igual: cada mudança de contrato público do Core muda `CORE_API_VERSION` e obriga a relançar todas as Capabilities | Manter a regra e agrupar mudanças, ou rever a regra |
| RFC-0002 | todos os que mudam o Core | A lista pública é fixada por teste | Cada adição atualiza RFC, teste, CHANGELOG e matriz |
| RFC-0001, seção 9; D-16 | 5 | Coerente com histórico fora do Core; o port atual não entrega contexto ao destino | Decidir a forma do destino SQL, se houver necessidade real |
| ADR-0011 | 5 | `configure_logging` cobre só stream | Guia para arquivo ou extensão da API pública |
| ADR-0007; `SECURITY.md` | 7, 8 | Cofre como resolvedor em pacote Provider já está previsto. Tabela SQL não está entre as origens admitidas de segredos | Decisão de segurança explícita para qualquer armazenamento em SQL |
| ADR-0005; `GOVERNANCE.md`, seção 8; ADR-0013 | 6, 8, 9 | Key Vault, Excel e feriados trariam as primeiras dependências de terceiros em tempo de execução. `tools/e2e.py` instala com `--no-index`; lock com hashes e análise de licenças continuam pendentes; a CI inclui Python 3.14 e 3.15 | Definir a política antes do primeiro Provider com dependência |
| ADR-0010 | 3, 4 | Sem retry por padrão. Reprocessar um item ou reenviar um aviso precisa ser política explícita e implica entrega "pelo menos uma vez" | Aceitar a semântica nas RFCs 0007 e 0008 |
| ADR-0001; ADR-0015 | todos | Cada pacote novo altera `pyproject.toml` da raiz, `tools/build_packages.py` e `tools/test_boundaries.py` | Um pacote por Pull Request |

## 5. O que este diagnóstico não responde

Faltam informações de um projeto consumidor real para definir contratos de fila, mapeamentos, login e calendários, e para escolher canais de notificação e o cofre de segredos. A lista está na [RFC-0004, seção 7](../rfc/0004-controles-reutilizaveis-escopo-e-sequencia.md). Nenhuma regra de negócio foi suposta para preencher essas lacunas.
