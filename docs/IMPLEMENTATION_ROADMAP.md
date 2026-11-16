# Roadmap de implementação — Orchestrator

| Campo | Valor |
|---|---|
| Atualizado em | 2026-11-15 |
| Situação | Fases 0 a 4 executadas, com as exceções listadas em cada fase; Fase 5 parcial; Fase 6 fora do escopo; Fase 7 em andamento: Core, SQL e SQLite 0.2.0 aprovados pelo responsável (DE-1) e consolidados na branch local `feature/core-0.2`, sem push nem PR |
| Decisões | [DECISIONS.md](DECISIONS.md) (D-00 a D-25 tomadas; respostas de 2026-11-15 às RFCs 0004 a 0012, decisões de encaminhamento DE-1 a DE-4 e aceite das RFCs 0004 a 0012 em 2026-11-15) |

Legenda: **Concluída** (feito e verificado), **Parcial** (feito em parte; o restante está descrito), **Pendente do responsável** (exige acesso ou autoridade que a entrega não tinha), **Adiada** (decisão explícita de fazer depois), **Implementada, aguardando aceite** (código e testes na árvore de trabalho, sem commit; a RFC de origem ainda não foi aceita), **Aprovada, aguardando integração** (implementação aprovada pelo responsável como decisão de encaminhamento, em branch local sem push; a RFC de origem foi aceita depois, em 2026-11-15), **Proposta** (RFC escrita, nada implementado), **Bloqueada** (falta a decisão indicada).

---

## 1. Princípios do plano

1. Recuperar antes de construir.
2. Decidir antes de codificar: cada contrato nasce de uma ADR ou RFC.
3. Entregas pequenas, cada uma do tamanho de um Pull Request, com critério de aceite verificável.
4. Provar com um consumidor instalado a partir do pacote.
5. Core pequeno.

## 2. Visão geral

| Fase | Objetivo | Situação |
|---|---|---|
| 0 | Recuperar o repositório e completar o diagnóstico | Concluída, com histórico novo; o remoto voltou a ser acessível em 2026-11-13 e não contém os commits de julho |
| 1 | Fundação de governança | Parcial: tudo o que é arquivo está feito; configurações do GitHub pendentes do responsável |
| 2 | Decisões e contratos do Core | Concluída |
| 3 | MVP técnico: `orchestrator-core` 0.1.0 | Concluída; a CI do GitHub passou em `e8eaabe` e em `564dd24` (status geral das execuções; jobs individuais não conferidos) |
| 4 | Primeira Capability e primeiro Provider | Concluída, exceto o segundo Provider (adiado) |
| 5 | Distribuição e releases | Parcial: workflow de release e matriz de compatibilidade prontos; nada publicado |
| 6 | Evolução futura | Fora do escopo até a 1.0 (ADR-0016) |
| 7 | Controles reutilizáveis (RFC-0004 a RFC-0012) | Em andamento: RFCs aceitas em 2026-11-15; duas fatias implementadas, aguardando integração; as demais, bloqueadas por decisões (seção 10) |

---

## 3. Fase 0 — Recuperação e diagnóstico

| ID | Entrega | Situação |
|---|---|---|
| E0.0 | Cópia de segurança da pasta | Coberta pelo commit-raiz e pela tag `archive/scaffold-2026-07`, que guardam todo o conteúdo da pasta |
| E0.1 | Repositório íntegro | Concluída por histórico novo: o remoto e a pasta de origem não estavam acessíveis ([guia](guides/recuperacao-do-historico.md)) |
| E0.1b | Trabalho não versionado commitado | Concluída: está no commit-raiz |
| E0.2 | Alterações da auditoria por PR | Substituída: entram no histórico novo; o PR acontece na reconciliação com o remoto |
| E0.3 | Auditoria complementar do código | Concluída em 2026-11-11 ([CODE_AUDIT](audit/CODE_AUDIT.md)) |
| E0.4 | Verificação do remoto e dos controles do GitHub | Parcial: remoto e CI conferidos pelas páginas públicas em 2026-11-15; proteção de `main` e controles de segurança exigem acesso administrativo |
| E0.5 | Decisões D-00, D-01, D-02 e D-23 | Concluída (ADR-0001, 0002, 0003, 0017) |

## 4. Fase 1 — Fundação de governança

| ID | Entrega | Situação |
|---|---|---|
| E1.1 | Aplicação de D-01 | Concluída: incubação em `packages/` (ADR-0001) |
| E1.2 | Higiene de branches e arquivos | Parcial: `.gitattributes`, `.gitignore`, remoção de `egg-info`, `stage.py`, duplicatas e pastas vazias feitas. Pendentes do responsável: apagar as branches antigas no remoto, executar `git clean` e recriar o `.venv` na pasta ([guia](guides/recuperacao-do-historico.md)) |
| E1.3 | Estrutura documental | Concluída: `docs/adr`, `docs/rfc`, índices, README, CHANGELOG, CONTRIBUTING, SECURITY, ROADMAP, CLAUDE.md, verificação automática de links (`tools/check_docs.py`) |
| E1.4 | Base de qualidade | Concluída: Ruff, MyPy estrito, Pytest e coverage configurados; ferramentas fixadas em `requirements/dev.txt`. Lock com hashes adiado (ADR-0013) |
| E1.5 | CI e proteção de `main` | Parcial: a CI rodou no GitHub com sucesso (execuções #1 e #5); proteção de `main` pendente do responsável |
| E1.6 | Triagem dos PRs do Dependabot | Concluída pelo responsável em 2026-11-13: PRs #1 (ações) e #2 (ferramentas) integrados, com merge commit em vez de squash (ADR-0018) |

## 5. Fase 2 — Decisões e contratos

| ID | Entrega | Situação |
|---|---|---|
| E2.1 | ADRs de D-03, D-04, D-05 | Concluída (ADR-0004, 0005, 0006) |
| E2.2 | RFC-0001: ciclo de vida | Concluída |
| E2.3 | ADRs de D-08, D-09, D-10, D-12, D-14 | Concluída (ADR-0007 a 0011) |
| E2.4 | Protótipo descartável | Substituída: a implementação foi feita contra as RFCs e os exemplos validaram a ergonomia |
| E2.5 | RFC-0002: escopo e superfície pública | Concluída |
| E2.6 | ARCHITECTURE e SECURITY atualizados | Concluída |

## 6. Fase 3 — `orchestrator-core` 0.1.0

| ID | Entrega | Situação |
|---|---|---|
| M1 | Esqueleto do pacote | Concluída: layout `src/`, `py.typed`, versão única, wheel e sdist |
| M2 | Erros, contexto, resultado | Concluída |
| M3 | Pipeline e os oito estágios | Concluída; matriz de falha com erro injetado em cada estágio |
| M4 | Configuração e segredos | Concluída; teste de precedência e de valor-sentinela |
| M5 | Capability, registry, escopo de recursos | Concluída |
| M6 | Logging, eventos, métricas | Concluída; correlação verificada em todos os logs da execução |
| M7 | Retry, cancelamento, prazo | Concluída, com relógio falso |
| M8 | Fachada pública, documentação, apoio a testes | Concluída; teste da lista de nomes públicos e das fronteiras |
| M9 | Projeto consumidor de exemplo | Concluída: `examples/hello-automation` e `examples/sales-report`, instalados só a partir dos wheels num ambiente virtual limpo e executados fora da árvore de fontes (`python -m tools.e2e`) |
| M10 | Preparação da release 0.1.0 | Concluída: CHANGELOG, tag local e build reproduzível verificado |

Critérios de aceite do MVP e situação: [RFC-0002, seção 3](rfc/0002-escopo-do-mvp-e-api-publica.md).

## 7. Fase 4 — Primeira Capability e primeiro Provider

| ID | Entrega | Situação |
|---|---|---|
| E4.1 | RFC da Capability | Concluída (RFC-0003) |
| E4.2 | `orchestrator-sql` | Concluída; depende só do Core; suíte de conformidade publicada |
| E4.3 | `orchestrator-sqlite` | Concluída; aprovado na suíte de conformidade |
| E4.4 | Segundo Provider | Adiada: sem segundo banco disponível no ambiente da entrega. A troca por configuração foi provada com o mesmo Provider; próximo passo: `orchestrator-postgres` |
| E4.5 | Verificação de extensibilidade | Concluída: nenhuma mudança de contrato no Core; uma correção de robustez registrada em commit próprio |

## 8. Fase 5 — Distribuição e releases

| Entrega | Situação |
|---|---|
| Canal de publicação | Decidido: tags e artefatos em releases do GitHub; índice de pacotes exige RFC (RFC-0002) |
| Publicação automatizada | Workflow `release.yml` pronto; não executado |
| Notas de release e guias de migração | CHANGELOG por pacote; guia de release |
| Matriz de compatibilidade testada | `docs/COMPATIBILITY.md`; a CI testa os pacotes juntos |
| Análise de dependências e licenças, SBOM, proveniência | Pendente; nenhum pacote tem dependência de execução de terceiros |
| Modelos para novas Capabilities e Providers | Guia escrito; modelo de repositório adiado até a primeira separação de pacote |

## 9. Fase 6 — Evolução futura

Fora do escopo até a 1.0 do Core (ADR-0016).

---

## 10. Fase 7 — controles reutilizáveis

Origem: [RFC-0004](rfc/0004-controles-reutilizaveis-escopo-e-sequencia.md), seção 5, revista com as respostas de 2026-11-15. Classificação das respostas, conflitos (C1 a C34) e decisões pedidas: [reconciliação](audit/RFC_RESPONSE_RECONCILIATION.md). A ordem abaixo é a base de análise, não uma fila obrigatória: entra a próxima entrega que estiver decidida e independente.

### 10.1 Situação das entregas

| ID | Entrega | Origem | Situação | Depende de / bloqueio |
|---|---|---|---|---|
| E7.1 | Decisões sobre as RFCs 0004 a 0012 | RFC-0004 | Concluída: RFCs 0004 a 0012 aceitas em 2026-11-15; D-26 a D-33 e ADR-0020 registradas ([DECISIONS](DECISIONS.md), seção 5.1); RFCs 0013 e 0014 em proposta, com respostas | — |
| E7.2 | CI confirmada no GitHub | Roadmap, seção 11 | Concluída para a 0.1.0: execução #5 (`564dd24`) com os 10 jobs com sucesso, conferidos um a um em 2026-11-15; a 0.2.0 ainda não rodou na CI | — |
| E7.3 | `ctx.redact` e `ExecutionOutcome.error_info` | RFC-0005, 2.1 | Aprovada, aguardando integração (DE-1) | DECISIONS, pendências 7 e 9 |
| E7.4 | Orçamento de teardown (60 s; zero desliga) | RFC-0005, 2.2; resposta 1 | Aprovada, aguardando integração (DE-1) | DECISIONS, pendências 7 e 9; C27 |
| E7.5 | Subetapas (`ctx.step`), limite de 1.000, aninhamento, registro | RFC-0005, 2.3; respostas 2 e 3 | Aprovada, aguardando integração (DE-1) | DECISIONS, pendências 7 e 9 |
| E7.6 | Guia de encerramento por sinal, aplicado aos exemplos | RFC-0005, 2.4; resposta 4 | Aprovada, aguardando integração (DE-1); Windows só na CI | DECISIONS, pendências 7 e 9; C29 |
| E7.7 | Release 0.2.0 de Core, SQL e SQLite, num único PR | RFC-0004, DS-2 (vale a ADR-0009); DE-4 | Consolidada: branch local `feature/core-0.2` a partir de `564dd24`, com quatro commits, entregue num bundle; validações locais completas (seção 10.3) | DECISIONS, pendências 7 e 9; CI do PR; autorização para merge e tags |
| E7.8 | Credenciais no port SQL: `connect(secrets)` | RFC-0006, 2.1; resposta 5 | Aprovada, aguardando integração (DE-1) | DECISIONS, pendências 7 e 9 |
| E7.9 | `orchestrator-keyvault` | RFC-0006, 2.2; respostas 1 a 3 | Bloqueada. O cache por execução já está no `SecretStore` do Core 0.2.0 (resposta 3) | D-28 (lock com hashes antes de `azure-identity` e `azure-keyvault-secrets`), cofre real para o teste de integração |
| E7.10 | `orchestrator-notifications`: contrato, canal em memória, suíte de conformidade, estágios de ciclo de vida | RFC-0007; D-33 | Implementada na branch local `feature/notifications`, sem push: 59 testes, conformidade aprovada | Push e PR (DECISIONS, pendência 9) |
| E7.11 | `orchestrator-notifications-smtp` | RFC-0007, seção 6 | Implementada na branch local `feature/notifications-smtp`, sem push: servidor SMTP local, suíte de conformidade; não testado contra servidor real | Push e PR; validação com o servidor do ambiente real |
| E7.12 | `orchestrator-notifications-teams` | RFC-0007, seção 6 | Implementada na branch local `feature/notifications-teams`, sem push: servidor HTTP local, suíte de conformidade; formato do cartão não validado contra o Teams | Push e PR; validação com o fluxo de Workflows do ambiente real |
| E7.13 | Logs em TXT (estrutura de pastas da resposta 1) e registros em arquivo | RFC-0009 | Implementada na branch local `feature/records-file`, sem push: `orchestrator-records-file` 0.1.0, 48 testes, inclusive quatro processos reais na mesma pasta (Linux) | Confirmar as hipóteses de C16 e C19 (README do pacote); push e PR; teste em Windows e em pasta de rede |
| E7.14 | Registros ou logs em SQL | RFC-0009, 2.3 | Bloqueada | C18, DS-1 |
| E7.15 | Limite de linhas na Capability SQL | RFC-0008, seção 6 | Aguardando consumidor (a fila) | E7.17 |
| E7.16 | Segundo Provider SQL (SQL Server, pela sintaxe da RFC-0008) | Roadmap, E4.4 | Bloqueada | C9, DS-3 |
| E7.17 e E7.18 | Fila e Provider SQL | RFC-0008 | Bloqueada | C5 a C11, DS-1, E7.15, E7.16 |
| E7.19 e E7.20 | Mapeamentos | RFC-0010 | Bloqueada; contrato a refazer para localizadores de interface | C3, C20, C22 |
| E7.21 e E7.22 | Calendários | RFC-0011 | E7.21 implementada na branch local `feature/calendar`, sem push: `orchestrator-calendar` 0.1.0 com fonte em arquivo (TOML, CSV, JSON), 82 testes. E7.22 (fontes SQL e Excel) planejada; o Provider de feriados padrão saiu do plano (feriados manuais) | Push e PR; exemplo de consumidor real (C3); fontes SQL e Excel quando houver caso |
| E7.23 | Subetapas padrão (opção C): finalização do ciclo de vida e de sistemas e processos | RFC-0005, resposta 3; DE-2; [RFC-0014](rfc/0014-subetapas-padrao-de-finalizacao.md) | Proposta, com respostas do responsável (2026-11-15); nada implementado | Aceite da RFC-0014; DS-4 para o pacote de processos; API 0.3 do Core (ADR-0009); DS-7 |
| E7.24 | Valores de segredos em SQL | DE-3; [RFC-0013](rfc/0013-segredos-em-sql-avaliacao-de-seguranca.md) | Proposta, com respostas do responsável (2026-11-15); implementação vedada até o aceite | Perguntas da RFC-0013, seção 8; DS-3 |
| — | Autenticação por sistema | RFC-0012 | Aceita, condicional; observação do aceite: caso de exemplo com mapeamentos simples usando o Google | C26: Capability de acesso (navegador), que depende de terceiros (D-28); E7.19 |

### 10.2 O que as entregas implementadas mudam

| Pacote | Arquivos principais | Contrato público |
|---|---|---|
| `orchestrator-core` 0.2.0 | `_context.py` (`step`, `redact`, `stages`, teardown), `_runtime.py`, `_results.py` (`StepOutcome`, `StepRecord`, `error_info`), `_events.py`, `_config.py`, `_stages.py` (falha de destino), `_correlation.py`, `logs.py`, `testing.py` (`make_secret_store`) | RFC-0002, seção 2.1; `tests/test_public_api.py` |
| `orchestrator-sql` 0.2.0 | `_provider.py` (`connect(secrets)`), `_capability.py`, `testing.py` (`secret_resolvers`, teste de credenciais) | RFC-0003, seção 3 |
| `orchestrator-sqlite` 0.2.0 | `_provider.py` | — |
| Exemplos 0.2.0 | `__main__.py` dos dois exemplos (sinais), faixas de dependência | — |

Testes novos: `test_steps.py`, `test_teardown_budget.py`, `test_signals.py` (subprocesso), acréscimos em `test_pipeline.py`, `test_secrets.py`, `test_config.py`, `test_observability.py` e `test_public_api.py`; no SQL, `test_credentials.py`; no SQLite, a suíte de conformidade com um Provider protegido por senha; nos exemplos, a ligação dos sinais.

Correções da consolidação ([CORE_020_CONSOLIDATION](audit/CORE_020_CONSOLIDATION.md), seção 4): `ErrorInfo.from_exception` (`_results.py`) tolera exceções cujo `__str__` falha, e `_StepScope.__enter__` (`_context.py`) desfaz a subetapa corrente quando a publicação de `StepStarted` é interrompida. Testes de regressão em `test_pipeline.py` e `test_steps.py`.

### 10.3 Validação das entregas implementadas

Executada em 2026-11-15, Linux, Python 3.13.18, com ruff 0.16.9, mypy 2.3.1, pytest 9.1.1 e setuptools 84.0.0 (as versões fixadas em `e8eaabe`; a CI usa as de `origin/main`).

| Comando | Resultado |
|---|---|
| `ruff check .` | All checks passed |
| `ruff format --check .` | 141 files already formatted |
| `mypy` | Success: no issues found in 48 source files |
| `pytest` | 259 passed, 1 skipped |
| `python tools/check_docs.py` | saída 0 |
| `python -m pytest tools` | 14 passed |
| `python tools/build_packages.py --check` | reproducible: 6 artifacts (0.2.0) |
| `python -m tools.e2e` | e2e ok (wheels 0.2.0 num ambiente limpo, exemplos fora da árvore) |
| Cobertura de linhas estimada (`sys.monitoring`, sem ramos) | 96,7% |

Não verificado nesta sessão: Windows (inclusive o teste de `CTRL_BREAK_EVENT`), Python 3.14 e 3.15, cobertura de ramos com `coverage.py`, ferramentas nas versões de `origin/main`. Tudo isso roda na CI do PR.

## 11. Próximas entregas recomendadas

1. **Responsável**: importar a branch `feature/core-0.2` do bundle ([consolidação](audit/CORE_020_CONSOLIDATION.md), seção 8) e revisar os quatro commits.
2. **Responsável**: autorizar o push e o PR (pendência 9 de [DECISIONS](DECISIONS.md)); a pendência 7 foi resolvida pelo aceite das RFCs em 2026-11-15. A CI do PR confere Windows, 3.14, 3.15, cobertura de ramos e as ferramentas de `origin/main`.
3. Responder às perguntas das RFCs 0013 e 0014 e aos itens ainda abertos da reconciliação, seção 8 (3 a 5 e 7 a 10). Cada resposta desbloqueia uma entrega da seção 10.1 sem esperar as outras.
4. Lock com hashes das ferramentas de desenvolvimento (ADR-0013), pré-requisito do primeiro pacote com dependência de terceiros (DS-3).
5. Proteção de `main` e merge só por squash (ADR-0014, ADR-0018).

## 12. Riscos

| Risco | Mitigação |
|---|---|
| Implementação antes do aceite formal das RFCs (`GOVERNANCE.md`, seção 5) | Implementações aprovadas como encaminhamento (DE-1); as RFCs de origem foram aceitas em 2026-11-15 (DECISIONS, seção 5), e o código fica numa branch local, fora de `main`, até a autorização de push e PR (pendência 9) |
| As três 0.2.0 só funcionam juntas (ADR-0009) | Um único PR; matriz em `docs/COMPATIBILITY.md` |
| Teardown sem limite quando `teardown_timeout = 0` | Padrão de 60 s; o guia de sinais orienta o tempo de espera do supervisor |
| Encerramento forçado não passa pelo Finished | Limite físico; documentado no guia; um supervisor externo pode apontar execuções sem Finished |
| Teste de `CTRL_BREAK_EVENT` não executado localmente | Roda na CI do Windows; se o runner não tiver console, o teste é ignorado com motivo |
| Ferramentas da CI mais novas que as da validação local | A CI do PR é a evidência válida; a consolidação lista o que não foi verificado localmente |
| Bundle desatualizado se `origin/main` avançar antes da importação | O bundle só exige `564dd24`; se `origin/main` avançar, basta um merge de `origin/main` na branch antes do PR (sem reescrever histórico) |
| Acoplamento acidental entre pacotes incubados | Testes de fronteira e dependências declaradas por pacote |
| Contratos congelados cedo | Antes da 1.0, versão menor pode quebrar; exemplos e suítes de conformidade detectam regressões |
