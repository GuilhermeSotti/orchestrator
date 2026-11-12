# Roadmap de implementação — Orchestrator

| Campo | Valor |
|---|---|
| Atualizado em | 2026-11-12 |
| Situação | Fases 0 a 4 executadas, com as exceções listadas em cada fase; Fase 5 parcial; Fase 6 fora do escopo |
| Decisões | [DECISIONS.md](DECISIONS.md) (D-00 a D-25, todas tomadas) |

Legenda: **Concluída** (feito e verificado), **Parcial** (feito em parte; o restante está descrito), **Pendente do responsável** (exige acesso ou autoridade que a entrega não tinha), **Adiada** (decisão explícita de fazer depois).

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
| 0 | Recuperar o repositório e completar o diagnóstico | Concluída, com histórico novo (o remoto continua inacessível) |
| 1 | Fundação de governança | Parcial: tudo o que é arquivo está feito; configurações do GitHub pendentes do responsável |
| 2 | Decisões e contratos do Core | Concluída |
| 3 | MVP técnico: `orchestrator-core` 0.1.0 | Concluída; Windows e Python 3.14 e 3.15 dependem da primeira execução da CI |
| 4 | Primeira Capability e primeiro Provider | Concluída, exceto o segundo Provider (adiado) |
| 5 | Distribuição e releases | Parcial: workflow de release e matriz de compatibilidade prontos; nada publicado |
| 6 | Evolução futura | Fora do escopo até a 1.0 (ADR-0016) |

---

## 3. Fase 0 — Recuperação e diagnóstico

| ID | Entrega | Situação |
|---|---|---|
| E0.0 | Cópia de segurança da pasta | Coberta pelo commit-raiz e pela tag `archive/scaffold-2026-07`, que guardam todo o conteúdo da pasta |
| E0.1 | Repositório íntegro | Concluída por histórico novo: o remoto e a pasta de origem não estavam acessíveis ([guia](guides/recuperacao-do-historico.md)) |
| E0.1b | Trabalho não versionado commitado | Concluída: está no commit-raiz |
| E0.2 | Alterações da auditoria por PR | Substituída: entram no histórico novo; o PR acontece na reconciliação com o remoto |
| E0.3 | Auditoria complementar do código | Concluída em 2026-11-11 ([CODE_AUDIT](audit/CODE_AUDIT.md)) |
| E0.4 | Verificação do remoto e dos controles do GitHub | Pendente do responsável |
| E0.5 | Decisões D-00, D-01, D-02 e D-23 | Concluída (ADR-0001, 0002, 0003, 0017) |

## 4. Fase 1 — Fundação de governança

| ID | Entrega | Situação |
|---|---|---|
| E1.1 | Aplicação de D-01 | Concluída: incubação em `packages/` (ADR-0001) |
| E1.2 | Higiene de branches e arquivos | Parcial: `.gitattributes`, `.gitignore`, remoção de `egg-info`, `stage.py`, duplicatas e pastas vazias feitas. Pendentes do responsável: apagar as branches antigas no remoto, executar `git clean` e recriar o `.venv` na pasta ([guia](guides/recuperacao-do-historico.md)) |
| E1.3 | Estrutura documental | Concluída: `docs/adr`, `docs/rfc`, índices, README, CHANGELOG, CONTRIBUTING, SECURITY, ROADMAP, CLAUDE.md, verificação automática de links (`tools/check_docs.py`) |
| E1.4 | Base de qualidade | Concluída: Ruff, MyPy estrito, Pytest e coverage configurados; ferramentas fixadas em `requirements/dev.txt`. Lock com hashes adiado (ADR-0013) |
| E1.5 | CI e proteção de `main` | Parcial: workflows escritos e equivalentes executados localmente; proteção de `main` pendente do responsável; a primeira execução no GitHub ainda não aconteceu |
| E1.6 | Triagem dos PRs do Dependabot | Pendente do responsável |

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

## 10. Próximas entregas recomendadas

1. **Responsável**: limpar a pasta e recriar o `.venv`, recuperar o acesso ao remoto, reconciliar o histórico e aplicar a proteção de `main` ([guias](guides/README.md)).
2. Primeira execução da CI no GitHub: confirmar Windows, Python 3.14 e 3.15 e os SHAs das ações.
3. Lock com hashes das ferramentas de desenvolvimento (ADR-0013).
4. `orchestrator-postgres` como segundo Provider, com PostgreSQL na CI (E4.4).
5. Escolha do primeiro projeto consumidor real e da próxima Capability a partir dele.

## 11. Riscos

| Risco | Mitigação |
|---|---|
| Histórico local sem ancestral comum com o remoto | Procedimento de reconciliação documentado, com `merge -s ours` preservando os dois |
| Mudanças no remoto depois de 2026-07-06 não conhecidas | Comparar `6232d68..origin/main` antes de reconciliar |
| Primeira execução da CI falhar por ambiente (Windows, 3.14, 3.15, SHAs) | Tudo foi verificado localmente em Linux 3.13; falhas de ambiente ficam visíveis no primeiro PR |
| Acoplamento acidental entre pacotes incubados | Testes de fronteira e dependências declaradas por pacote |
| Contratos congelados cedo | Antes da 1.0, versão menor pode quebrar; exemplos e suítes de conformidade detectam regressões |
