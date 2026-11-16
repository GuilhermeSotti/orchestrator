# Consolidação do Core 0.2.0

| Campo | Valor |
|---|---|
| Data | 2026-11-15 |
| Origem | Decisões de encaminhamento DE-1 a DE-4 do responsável ([DECISIONS](../DECISIONS.md), seção 4) |
| Escopo | `orchestrator-core`, `orchestrator-sql` e `orchestrator-sqlite` 0.2.0, os dois exemplos e a documentação correspondente; RFCs 0013 e 0014, em proposta |
| Situação das RFCs | 0004 a 0014 em "Proposta. Não aceita". Nenhum status foi alterado |
| Autor | Claude, a pedido do responsável |
| Revisão independente | Não houve. O ai-harness continua sem integração executável nesta sessão ([reconciliação](RFC_RESPONSE_RECONCILIATION.md), seção 1.5); nada aqui é resultado de agente independente |

## 1. Resumo

- A 0.2.0 aprovada em 2026-11-15 (DE-1) foi auditada contra as RFCs de origem e a RFC-0002. Experimentos acharam dois defeitos, corrigidos num commit próprio; um deles já existia na 0.1.0 (seção 4).
- A compatibilidade foi comprovada com os wheels: os três pacotes 0.2.0 funcionam juntos, e a mistura com a 0.1.0 é recusada pelo pip e, se forçada, pelo registro de Capabilities (seção 5).
- Todas as ferramentas e testes passaram em Linux com Python 3.13 (seção 6). Windows, Python 3.14 e 3.15, cobertura de ramos e as versões novas das ferramentas não foram verificados nesta sessão; a 0.2.0 ainda não rodou na CI.
- A integração está na branch local `feature/core-0.2`, a partir de `564dd24`, com quatro commits, e chegou à pasta num bundle. Nenhum push, PR, merge, tag ou release (seção 8).
- Ficam pendentes, por dependerem de autorização ou de decisão: a CI da 0.2.0 e a regra de governança sobre RFC aceita antes da implementação (seção 9).

## 2. Estado inicial

### 2.1 Pasta do responsável

Não há terminal no computador do responsável. Os arquivos de `.git` foram copiados e examinados com `git` numa cópia; nada foi gravado em `.git`. Conferido às 15h56 e de novo às 17h28.

| Item | Situação | Como foi verificado |
|---|---|---|
| Branch atual | `main`, em `e8eaabe` | `HEAD` e `refs/heads/main` |
| `origin/main` | `564dd24`, quatro commits à frente de `main` | `refs/remotes/origin/main` e reflog |
| Último `fetch` | 2026-11-15, 15h56: `main` em `564dd24` e a branch `dependabot/pip/requirements/dev-tools-ff8c5acc02` em `968d478` | `FETCH_HEAD` |
| Índice | Igual à árvore de `e8eaabe` (159 entradas), sem nada preparado para commit | `git diff-index --cached e8eaabe` com o índice copiado |
| Árvore de trabalho | 57 arquivos rastreados modificados e 16 não rastreados, todos da entrega de 2026-11-15 (gravada às 13h10) ou dos documentos de 2026-11-14 com as respostas às RFCs (gravadas entre 11h51 e 12h16). Nenhum arquivo com data posterior à entrega | Datas de modificação; `git status` numa réplica da pasta |
| Refs locais de ferramentas | `refs/agents/*/checkpoints/turn/*`, criadas em 2026-11-13 entre 20h07 e 20h21; pelo nome, pontos de checkpoint de uma ferramenta de agente (inferido). Não foram usadas nem alteradas | Listagem de `.git/refs` |
| Reflogs antigos | `.git/logs/refs/heads/feature`, `feature-core` e `teste`, de julho de 2026, de branches que não existem mais. O de `feature` impede criar qualquer branch `feature/*` (seção 3) | Listagem de `.git/logs` e tentativa na cópia |

### 2.2 Os quatro commits de `origin/main`

| Commit | Origem | Conteúdo |
|---|---|---|
| `b04bfab` | Dependabot | `actions/setup-python` 7.0.0 → 7.1.0 (`ci.yml`, `release.yml`) e `actions/upload-artifact` 6.0.0 → 7.0.2 (`ci.yml`) |
| `968d478` | Dependabot | `requirements/dev.txt`: ruff 0.16.9 → 0.17.4, mypy 2.3.1 → 2.4.1, pytest 9.1.1 → 9.2.0, coverage 7.15.3 → 7.17.2, setuptools 84.0.0 → 84.2.1 |
| `4970e00`, `564dd24` | Merges dos PRs #1 e #2 no GitHub, em 2026-11-13, às 21h54 | Merge commit, não squash (DECISIONS, pendência 6) |

A 0.2.0 não altera nenhum desses três arquivos: o avanço de `main` é fast-forward e não conflita com as alterações locais.

### 2.3 CI no GitHub

Execução #5 do workflow CI, disparada pelo push em `main` em `564dd24`, conferida job a job pela API pública do GitHub em 2026-11-15:

| Job | Runner | Resultado |
|---|---|---|
| quality | ubuntu-latest | success |
| build | ubuntu-latest | success |
| tests, Python 3.13, 3.14 e 3.15 | ubuntu-latest | success nos três |
| tests, Python 3.13, 3.14 e 3.15 | windows-latest | success nos três |
| e2e | ubuntu-latest | success |
| e2e | windows-latest | success |

Os dez jobs rodaram entre 00h54 e 00h55 UTC de 2026-11-14. Na página de Actions, conferida nesta etapa, as execuções #1 a #3 terminaram com sucesso, a #4 foi cancelada (substituída pela #5) e não havia execução posterior à #5. A página da execução #5 avisa da migração do rótulo `ubuntu-latest` para o Ubuntu 26.

**Esta evidência é da 0.1.0.** O código da 0.2.0 nunca rodou na CI, porque nada foi enviado ao remoto.

### 2.4 Ambiente desta sessão

| Item | Situação |
|---|---|
| Sistema | Linux; Python 3.13.18; git 2.43.0 |
| Ferramentas | ruff 0.16.9, mypy 2.3.1, pytest 9.1.1 e setuptools 84.0.0, as versões fixadas em `e8eaabe`. As de `564dd24` não puderam ser instaladas, porque a instalação de pacotes está desligada nesta sessão |
| Cobertura | `coverage.py` ausente. Estimativa de linhas com `sys.monitoring`, sem ramos, que não substitui o gate de 90% da CI |
| Rede | O `git` desta sessão não alcança o GitHub. A API e as páginas públicas foram lidas pela ferramenta de leitura web |

## 3. Sincronização da `main` e criação da branch

O pedido era sincronizar com `git pull --ff-only` antes de criar a branch. Na pasta não há terminal, e o `git` da sessão não alcança o GitHub. Por isso o equivalente foi feito na cópia da sessão, com os objetos que o `fetch` da pasta trouxe às 15h56:

```text
git update-ref refs/remotes/origin/main 564dd24   # espelho do FETCH_HEAD da pasta
git merge --ff-only origin/main                   # e8eaabe..564dd24, fast-forward
git worktree add -b feature/core-0.2 <pasta> 564dd24
```

O fast-forward atualizou só `ci.yml`, `release.yml` e `requirements/dev.txt` e manteve as alterações locais. Na primeira tentativa, a criação da branch falhou com `unable to append to '.git/logs/refs/heads/feature/core-0.2': Not a directory`: o reflog antigo `feature` ocupa o lugar da pasta `feature/`. Ele foi movido para `.git/recovery-2026-11-15/` e a branch foi criada. Na pasta do responsável, o `git pull --ff-only` e essa mesma movimentação fazem parte do procedimento da seção 8.2.

## 4. Auditoria da 0.2.0

### 4.1 O que foi verificado

Três frentes: leitura dos módulos alterados contra a RFC-0005 (2.1 a 2.4), a RFC-0006 (2.1), as respostas 6 das RFCs 0007 e 0009 e a RFC-0002 (seção 2.1); experimentos com os caminhos de falha; testes e wheels.

| Item | Verificação | Resultado |
|---|---|---|
| `ctx.step`, aninhamento, nomes válidos, contexto fechado | `test_steps.py` (13 testes) | Conforme; P2 encontrado e corrigido |
| `runtime.max_steps` (padrão de 1.000) | `test_the_default_step_limit_is_1000` e `test_the_step_limit_truncates_the_record_but_not_events_or_metrics` | Conforme: o registro para no limite e marca `steps_truncated`; eventos e métricas continuam |
| `StepStarted`, `StepFinished`, `orchestrator.step.duration_seconds`, campo `step` nos logs, subetapas no resultado e no registro | `test_steps.py`, `test_observability.py` | Conforme |
| Isolamento entre execuções | `test_stress_concurrent_executions_with_nested_steps_do_not_mix`, `test_nested_executions_do_not_inherit_the_outer_step`, `test_concurrency.py` | Conforme |
| `runtime.teardown_timeout` (padrão de 60 s; zero desliga; negativo recusado) e `check`, `sleep`, `retry`, `remaining` e `deadline_exceeded` no teardown | `test_teardown_budget.py` (8 testes), `test_config.py` | Conforme. Zero desliga o limite, como respondido (C27: teardown sem fim continua sendo um risco documentado) |
| `ctx.redact` e `ExecutionOutcome.error_info` | `test_secrets.py`, `test_observability.py`; experimento P1 | Conforme; P1 encontrado e corrigido |
| `ctx.stages` | `test_context_lists_the_configured_stages` | Conforme |
| Falha de `ExecutionRecordSink` | `test_record_sink_failures_never_change_the_execution` e `test_record_sink_failure_does_not_mask_a_failed_execution` | Conforme: aviso no log, métrica `orchestrator.record_sink.errors` e status preservado |
| Encerramento por sinal | `test_signals.py` (subprocesso) e um teste em cada exemplo | Passou em Linux. No Windows, o teste de `CTRL_BREAK_EVENT` não foi executado aqui |
| `CORE_API_VERSION = "0.2"` e `testing.make_secret_store` | `test_public_api.py`, `test_make_secret_store_resolves_with_a_private_masking_registry` | Conforme |
| Core sem dependências de terceiros nem de Capabilities | `tools/test_boundaries.py` | Conforme |
| `SqlProvider.connect(secrets)` e `SqlCapability.open` com `ctx.secrets` | `test_session_and_capability.py`, `test_the_capability_hands_the_execution_secrets_to_the_provider` | Conforme |
| Erros e credenciais por referência | `test_a_wrong_password_fails_provisioning_without_the_value`, `test_the_password_never_reaches_logs_events_records_or_the_provider` | Conforme: a senha não aparece em logs, eventos, registros, erros nem no Provider |
| Conformidade de Providers | Suíte de `orchestrator_sql.testing` com o SQLite e com um Provider de teste protegido por senha (`test_contract.py` do SQLite, 19 testes) | Conforme |
| API pública | `test_public_api.py` contra a RFC-0002, seção 2.1 | Coerente |
| CHANGELOGs, matriz e RFCs | Leitura cruzada com o código | Coerentes depois desta etapa: "na árvore de trabalho, sem commit" passou a "branch local `feature/core-0.2`" |

### 4.2 Problemas encontrados e correções

| # | Problema | Efeito | Desde | Correção | Teste de regressão |
|---|---|---|---|---|---|
| P1 | `ErrorInfo.from_exception` chamava `str(error)` sem proteção | Com uma exceção cujo `__str__` falha (possível em bibliotecas de terceiros), `Runtime.run` lançava `RuntimeError` e não rodava teardown, registro nem `ExecutionFinished` | 0.1.0 | A mensagem passa a ser `<exception str() failed>` | `test_an_exception_whose_str_fails_does_not_break_the_pipeline` |
| P2 | `_StepScope.__enter__` marcava a subetapa como corrente antes de publicar `StepStarted` | Uma `BaseException`, como `KeyboardInterrupt`, num assinante deixava a subetapa corrente no resto da execução: subetapas seguintes com o pai errado e logs com o nome errado | 0.2.0 | O `__enter__` desfaz a marcação antes de relançar | `test_an_interrupt_in_a_step_started_handler_does_not_leak_the_step` |

Saída dos experimentos:

```text
0.1.0 (e8eaabe):       P1 run RAISED RuntimeError str() is broken | teardown ran: False
0.2.0 com a correção:  P1 run returned: failed | teardown ran: True
0.2.0 com a correção:  P2 current step after a failed StepStarted handler: [None]
```

As correções vieram depois da aprovação DE-1. Estão num commit próprio (`fix(core)`), para revisão no PR, e no CHANGELOG do Core, seção "Corrigido".

### 4.3 Constatações sem correção nesta etapa

- Com várias falhas no `finalize`, o registro guarda só a mensagem do grupo (`3 errors in stage 'finalize' (3 sub-exceptions)`), e os erros individuais ficam só em `ExecutionResult.teardown_errors`. A correção muda o contrato público e está proposta na [RFC-0014](../rfc/0014-subetapas-padrao-de-finalizacao.md), seção 2 (lacunas L1 a L4).
- `runtime.teardown_timeout = 0` desliga o limite, conforme a resposta do responsável (C27).

## 5. Contrato público e compatibilidade

### 5.1 Contrato

- **Core**: só acréscimos de nomes e membros ([RFC-0002](../rfc/0002-escopo-do-mvp-e-api-publica.md), seção 2.1, fixados por `tests/test_public_api.py`). Duas mudanças de comportamento estão documentadas no CHANGELOG: os métodos de tempo do contexto durante o teardown e a falha de destino de registro, que não muda mais o status.
- **SQL**: mudança incompatível em `SqlProvider.connect(secrets)`, com rodapé `BREAKING CHANGE` no commit e registro no CHANGELOG do pacote.
- **SQLite**: adota a assinatura nova, sem nomes públicos novos.
- **Matriz** ([COMPATIBILITY](../COMPATIBILITY.md)): os três pacotes 0.2.0 exigem `>=0.2,<0.3` entre si.
- **ADR-0009**: antes da 1.0, a API do Core precisa ser igual à exigida pela Capability. Por isso os três pacotes vão num único PR e numa única release.

### 5.2 Evidência com os wheels

Wheels construídos da branch com `tools/build_packages.py --check` e instalados sem índice de pacotes, em ambientes virtuais novos:

| Cenário | Resultado |
|---|---|
| A. `pip install` de `orchestrator-core==0.2.0` com `orchestrator-sql==0.1.0` | Recusado: `ResolutionImpossible` |
| B. Os mesmos dois, forçados com `--no-deps` | `pip check`: `orchestrator-sql 0.1.0 has requirement orchestrator-core<0.2,>=0.1, but you have orchestrator-core 0.2.0`. Ao registrar a Capability: `IncompatibleCapabilityError: capability 'sql' (SqlCapability) requires Core API 0.1, but this Core provides 0.2` |
| C. Os três 0.2.0 | `pip check`: `No broken requirements found`. `SELECT 42` pelo Provider SQLite termina `succeeded`, com resultado 42 |

`python -m tools.e2e` também confirmou a instalação só a partir dos wheels, `pip check` limpo, os marcadores de tipo, os scripts de console e os dois exemplos executados fora da árvore de fontes.

## 6. Validação

### 6.1 Ponta da branch

No ambiente da seção 2.4, na raiz de uma cópia da branch (`git worktree`):

| Comando | Resultado |
|---|---|
| `ruff check .` | All checks passed! |
| `ruff format --check .` | 144 files already formatted |
| `mypy` | Success: no issues found in 48 source files |
| `pytest` | 261 passed, 1 skipped |
| `python tools/check_docs.py` | saída 0 |
| `python -m pytest tools` | 14 passed |
| `python tools/build_packages.py --check` | reproducible: 6 artifacts (0.2.0) |
| `python -m tools.e2e` | e2e ok |
| Cobertura estimada de linhas, três pacotes | 96,7% (3.269 de 3.381 linhas). Com os exemplos, 96,6% |

O teste ignorado é um doctest marcado `+SKIP`. A contagem do `ruff format` inclui os arquivos Markdown, que o ruff 0.16.9 examina por padrão.

### 6.2 Por commit

| Commit | Verificações | Resultado |
|---|---|---|
| `c914b9e` (docs) | `check_docs` | saída 0 |
| `099800e` (feat!) | ruff, formatação, mypy, pytest, `check_docs`, `pytest tools` | 259 passed, 1 skipped; demais sem falhas |
| `8c23bad` (fix) | ruff, formatação, mypy, pytest, `check_docs` | 261 passed, 1 skipped; demais sem falhas |
| Quarto commit (docs, este documento) | Todos os da seção 6.1 | Seção 6.1 |

Em relação aos registros anteriores: a linha de base de 2026-11-15 tinha 214 testes aprovados, 1 ignorado e 96,4% estimados; a entrega da 0.2.0, 259 aprovados, 1 ignorado e 96,7%. Os dois testes a mais são os de regressão da seção 4.2.

### 6.3 Não verificado nesta sessão

- Windows, inclusive o teste de `CTRL_BREAK_EVENT` e o e2e.
- Python 3.14 e 3.15.
- `coverage.py`, com ramos e o mínimo de 90% da CI.
- Ferramentas nas versões de `564dd24`: ruff 0.17.4, mypy 2.4.1, pytest 9.2.0, coverage 7.17.2 e setuptools 84.2.1.

Tudo isso roda na CI do PR. Nenhuma dessas combinações foi declarada validada.

## 7. Segredos e arquivos indevidos

- Diff de `564dd24` até a ponta da branch: 77 arquivos (19 novos e 58 alterados), só código Python, testes, Markdown e `pyproject.toml`. Nenhum `.env`, banco (`.db`, `.sqlite`), wheel, sdist, bundle ou outro binário.
- Busca no diff por padrões de credencial (`password=`, `Pwd=`, chaves privadas, tokens do GitHub, da AWS e do Slack, JWT) e por endereços de e-mail: só exemplos de documentação com referências (`env:`, `kv:`), endereços de `exemplo.com` e valores-sentinela fictícios dos testes de mascaramento.
- Autor e committer dos commits: `Claude Opus 5.5 <noreply@anthropic.com>`. Nenhum e-mail pessoal nos commits nem nos documentos. Os reflogs antigos da pasta têm dados pessoais e não foram copiados para nenhum documento.
- O bundle contém só os quatro commits, e o seu pré-requisito é `564dd24`.

## 8. Estado da integração

### 8.1 Situação

| Item | Valor |
|---|---|
| Branch | `feature/core-0.2`, local |
| Commit-base | `564dd24` (`origin/main` no `fetch` de 15h56) |
| Commits | `c914b9e` docs: diagnosticar o escopo dos controles reutilizáveis e propor as RFCs 0004 a 0012; `099800e` feat!: entregar Core, SQL e SQLite 0.2.0; `8c23bad` fix(core): preservar o teardown e a subetapa corrente em falhas raras; o quarto, docs: consolidar a 0.2.0, contém este documento |
| Arquivos | 77 em relação a `564dd24` (19 novos e 58 alterados): `git diff --stat 564dd24 feature/core-0.2` |
| `main` na pasta | `e8eaabe`, quatro commits atrás de `origin/main`; o procedimento da seção 8.2 faz o fast-forward |
| `main` na cópia da sessão | `564dd24` |
| `origin/main` | `564dd24` |
| Push, PR, merge, tag e release | Nenhum |
| Entrega na pasta | Bundle `orchestrator-core-0.2.bundle` na raiz. Os arquivos da árvore de trabalho ficaram com o conteúdo da ponta da branch, exceto `ci.yml`, `release.yml` e `requirements/dev.txt`, que chegam pelo `git pull --ff-only` |

Os commits seguem a ADR-0018 (Conventional Commits em português). O merge no GitHub deve ser por squash; a mensagem final do squash pode reunir as quatro.

### 8.2 Importar a branch na pasta

Procedimento testado numa réplica da pasta, com o mesmo `.git` e a mesma árvore de trabalho. Nenhum passo apaga arquivos: o que sai do lugar vai para `.git\recovery-2026-11-15\`.

```powershell
cd C:\Users\Particular\Projetos\orchestrator
# 1. Guardar o reflog antigo que impede criar branches feature/*
New-Item -ItemType Directory -Force .git\recovery-2026-11-15 | Out-Null
Move-Item .git\logs\refs\heads\feature .git\recovery-2026-11-15\logs-refs-heads-feature
# 2. Atualizar a main (fast-forward; não toca nos arquivos desta entrega)
git pull --ff-only
# 3. Importar a branch e guardar o bundle
git bundle verify .\orchestrator-core-0.2.bundle
git fetch .\orchestrator-core-0.2.bundle "refs/heads/feature/core-0.2:refs/heads/feature/core-0.2"
Move-Item .\orchestrator-core-0.2.bundle .git\recovery-2026-11-15\
# 4. Conferir que a pasta é igual à branch
git add -A
git diff --cached --stat feature/core-0.2
# 5. Passar para a branch
git switch feature/core-0.2
git status
git log --oneline -5
```

No passo 4, a saída deve ser vazia. Se aparecerem diferenças, não siga para o passo 5. Elas são alterações feitas na pasta depois desta entrega, ou commits que `origin/main` recebeu depois de `564dd24`. `git restore --staged .` desfaz o passo 4 sem mexer nos arquivos.

Por que `git add -A` antes de `git switch`: os arquivos da pasta já são os da branch, mas diferem de `main`. Sem prepará-los, o Git recusa a troca para não sobrescrever alterações locais. Com tudo preparado, a troca mantém os arquivos como estão. O passo 5 deve terminar com `nothing to commit, working tree clean`.

### 8.3 Prontidão para PR

| Definition of Done (`GOVERNANCE.md`, seção 14) | Situação |
|---|---|
| Implementação segue contratos e arquitetura | Atendido (seção 4) |
| Type hints e docstrings | Atendido; mypy estrito sem erros |
| Ruff, formatação, MyPy e Pytest, com cobertura mínima | Atendido com as versões de `e8eaabe`; a cobertura com `coverage.py` e as versões novas ficam para a CI |
| Testes unitários, de integração e de estresse | Atendido: subetapas concorrentes, subprocesso de sinais, conformidade de Providers e e2e com wheels |
| Documentação, exemplos e CHANGELOG | Atendido |
| PR revisado | Pendente: PR não aberto |
| CI aprovada | Pendente: depende do push |
| RFC aceita antes da implementação (`GOVERNANCE.md`, seção 5) | Pendente (seção 9.1) |

A branch está tecnicamente pronta para PR. O PR depende de autorização e da decisão da seção 9.1.

### 8.4 O que exige autorização

- Push de `feature/core-0.2` e abertura do PR.
- Merge por squash (ADR-0018), tags `orchestrator-core/v0.2.0`, `orchestrator-sql/v0.2.0` e `orchestrator-sqlite/v0.2.0` e releases do GitHub.
- Aceite das partes implementadas ou exceção de governança (seção 9.1).
- Configurações do GitHub: só squash e proteção de `main` (DECISIONS, pendências 2 e 6).

## 9. Pendências e critérios não atendidos

### 9.1 Regra de RFC aceita antes da implementação

O `GOVERNANCE.md`, seção 5, pede RFC aceita antes da implementação. O responsável aprovou as implementações (DE-1) e manteve as RFCs em proposta. Para o merge, há três caminhos:

| Opção | Efeito | Risco |
|---|---|---|
| A. Aceitar formalmente as partes implementadas: RFC-0005, 2.1 a 2.4; RFC-0006, 2.1; respostas 6 das RFCs 0007 e 0009 | Status "aceita em parte" nessas RFCs e decisões D-26 em diante no DECISIONS; o resto continua em proposta | Baixo; usa o aceite por parte que a RFC-0005 já prevê |
| B. Registrar uma exceção de governança para a 0.2.0 | A regra continua valendo; a exceção fica registrada no DECISIONS | Abre precedente de implementação antes do aceite |
| C. Manter a 0.2.0 fora de `main` | Sem merge | A branch se afasta de `main` |

Recomendação técnica: opção A, que usa o mecanismo previsto e não abre precedente. A decisão é do responsável, e nenhuma das opções foi aplicada.

### 9.2 Critérios de conclusão desta etapa

| Critério | Situação |
|---|---|
| 1. Core, SQL e SQLite 0.2.0 auditados | Atendido (seção 4) |
| 2. Alterações aprovadas preservadas e organizadas | Atendido: quatro commits locais; nada foi descartado na pasta |
| 3. Compatibilidade dos três pacotes comprovada | Atendido com wheels em Linux e Python 3.13 (seção 5). Outros sistemas e versões dependem da CI |
| 4. Testes aplicáveis executados | Atendido em Linux, Python 3.13 e ferramentas de `e8eaabe`. **Não atendido** para Windows, 3.14, 3.15 e cobertura de ramos: exigem a CI, e o push não está autorizado |
| 5. Documentação atualizada | Atendido |
| 6. Proposta de subetapas registrada | Atendido: [RFC-0014](../rfc/0014-subetapas-padrao-de-finalizacao.md), em proposta |
| 7. RFC de segurança de SQL elaborada | Atendido: [RFC-0013](../rfc/0013-segredos-em-sql-avaliacao-de-seguranca.md), em proposta |
| 8. RFCs com status corretos | Atendido: 0004 a 0014 em proposta; 0006 e 0012 sem marcação de aceite |
| 9. Nenhuma implementação de funcionalidade bloqueada | Atendido: nenhum pacote novo, nenhuma dependência nova, nada da lista fora do escopo |
| 10. Evidências verificáveis | Atendido: comandos, saídas e commits neste documento |
| `git pull --ff-only` antes da branch | Equivalente executado na cópia da sessão (seção 3). Na pasta, faz parte da seção 8.2 |
| CI conferida por job | Atendido para a 0.1.0 (execução #5). Para a 0.2.0, depende do push |

### 9.3 Outras pendências

- Perguntas da RFC-0013 (seção 8) e da RFC-0014 (seção 6).
- DECISIONS, seção 2, pendências 1 a 6: histórico de julho, proteção de `main`, reporte privado de vulnerabilidades, titularidade, branch do Dependabot e merge por squash.
- Itens ainda abertos da [reconciliação](RFC_RESPONSE_RECONCILIATION.md), seção 8.
- Migração do `ubuntu-latest` para o Ubuntu 26, avisada pela CI: acompanhar na primeira execução da 0.2.0.

## 10. Continuação de 2026-11-15, noite

Acréscimo; as seções 1 a 9 ficam como estavam.

### 10.1 O que mudou

| Item | Situação |
|---|---|
| Aceite | RFCs 0004 a 0012 aceitas pelo responsável ([DECISIONS](../DECISIONS.md), seção 5); a pendência 7 e a regra da seção 9.1 ficaram resolvidas pelo aceite. RFCs 0013 e 0014 continuam em proposta, com as respostas do responsável |
| Commits novos nesta branch | `85a960d` registra o aceite e as respostas, conteúdo encontrado na pasta do responsável; `559570f` guarda segredos só durante a execução (RFC-0006, resposta 3); `e11379a` registra D-26 a D-33 e a ADR-0020 |
| Validação da ponta `e11379a` | `ruff check` sem erros; 145 arquivos formatados; `mypy` sem erros em 48 arquivos; `pytest` 264 aprovados e 1 ignorado; `check_docs` saída 0; `pytest tools` 14 aprovados; build reproduzível com 6 artefatos; `tools.e2e` ok; cobertura estimada de linhas 96,7% (3.289 de 3.401). Mesmo ambiente da seção 2.4 |
| Branches seguintes | Em pilha sobre esta, um pacote por Pull Request (RFC-0004, seção 2, regra 6): `feature/notifications` (`5621a65`, `9f04422`), `feature/notifications-smtp` (`974038f`, `d9095ab`, `0e05b08`), `feature/notifications-teams` (`7633a4c`, `951540f` com o exemplo `batch-check`, `7b96460`, `0205577`), `feature/records-file` (`32b0d6f`, `d3d38b2`) e `feature/calendar` (`048a3ca`, `1965806`, `c3e56bf`, `2967cb4` e a ponta com esta seção). Os commits `d9095ab`, `7b96460` e `2967cb4` são merges da branch de baixo, para levar correções sem reescrever o histórico; o squash do PR os elimina (ADR-0018) |

### 10.2 Importar na pasta

Substitui o procedimento da seção 8.2, que importava só esta branch. O bundle novo, `orchestrator-2026-11-15.bundle`, traz as seis branches; o pré-requisito continua `564dd24`. A pasta fica com o conteúdo da última branch da pilha, `feature/calendar`.

```powershell
cd C:\Users\Particular\Projetos\orchestrator
# 1. Guardar o reflog antigo que impede criar branches feature/*
New-Item -ItemType Directory -Force .git\recovery-2026-11-15 | Out-Null
Move-Item .git\logs\refs\heads\feature .git\recovery-2026-11-15\logs-refs-heads-feature
# 2. Atualizar a main (fast-forward)
git pull --ff-only
# 3. Importar as branches e guardar os dois bundles
git bundle verify .\orchestrator-2026-11-15.bundle
git fetch .\orchestrator-2026-11-15.bundle "refs/heads/feature/*:refs/heads/feature/*"
Move-Item .\orchestrator-2026-11-15.bundle, .\orchestrator-core-0.2.bundle .git\recovery-2026-11-15\
# 4. Conferir que a pasta é igual à última branch (a pasta .claude fica de fora)
git add -A -- . ':(exclude).claude'
git diff --cached --stat feature/calendar
# 5. Passar para a branch
git switch feature/calendar
git status
```

No passo 4, a saída deve ser vazia; se não for, siga a orientação da seção 8.2. A pasta `.claude`, com as definições de agentes do responsável, não está em nenhuma branch e continua fora do Git até o responsável decidir versioná-la.

### 10.3 Validação de cada branch

Cada ponta foi validada sozinha, numa cópia de trabalho limpa (`git worktree add --detach`), com os comandos da seção 2.4: `ruff check .`, `ruff format --check .`, `mypy`, `pytest`, `tools/check_docs.py`, `pytest tools`, `tools/build_packages.py --check` e `python -m tools.e2e`. Linux, Python 3.13.18, ruff 0.16.9, mypy 2.3.1, pytest 9.1.1, setuptools 84.0.0; em 2026-11-15, à noite.

| Branch | Ponta | Formatados | mypy | pytest | `pytest tools` | Artefatos | E2E |
|---|---|---:|---:|---|---:|---:|---|
| `feature/core-0.2` | `f500f9e` | 145 | 48 | 264 aprovados, 1 ignorado | 14 | 6 | ok |
| `feature/notifications` | `9f04422` | 159 | 59 | 324 aprovados, 1 ignorado | 15 | 8 | ok |
| `feature/notifications-smtp` | `0e05b08` | 166 | 62 | 356 aprovados, 1 ignorado | 16 | 10 | ok |
| `feature/notifications-teams` | `0205577` | 179 | 68 | 383 aprovados, 1 ignorado | 18 | 12 | ok, com `batch-check` e servidor SMTP local |
| `feature/records-file` | `d3d38b2` | 189 | 73 | 432 aprovados, 1 ignorado | 19 | 14 | ok, com log e registro gravados pelo wheel |
| `feature/calendar` | ponta com esta seção | 201 | 80 | 515 aprovados, 1 ignorado | 20 | 16 | ok, com arquivo de feriados lido pelo wheel |

Em todas: `ruff check` sem erros e `check_docs` com saída 0. Cobertura de linhas estimada na ponta `1965806` de `feature/calendar`, sobre os oito pacotes, com o mesmo método da seção 2.4 (`sys.monitoring`; `coverage.py` não está instalado aqui): 96,3% (5.209 de 5.409 linhas). Cobertura de branches não medida. Não executado: Windows, Python 3.14 e 3.15, CI do GitHub para qualquer código posterior à 0.1.0, servidores SMTP e Teams reais.
