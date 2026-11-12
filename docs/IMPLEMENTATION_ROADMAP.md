# Roadmap de implementação — Orchestrator

| Campo | Valor |
|---|---|
| Atualizado em | 2026-11-11, após a auditoria inicial (`docs/audit/INITIAL_AUDIT.md`) e a auditoria do código (`docs/audit/CODE_AUDIT.md`) |
| Substitui | O roadmap proposto no kit de contexto; as fases originais foram mantidas e detalhadas |
| Natureza | **Proposta para aprovação.** Nada aqui está concluído, exceto onde indicado |
| Decisões relacionadas | `docs/OPEN_DECISIONS.md` (IDs D-00 a D-25) |

---

## 1. Princípios do plano

1. **Recuperar antes de construir.** O Git local não funciona e há trabalho nunca versionado. Nenhuma implementação começa antes de isso estar resolvido.
2. **Decidir antes de codificar.** Cada contrato do Core nasce de um ADR ou de uma RFC aceitos.
3. **Entregas pequenas.** Cada entrega cabe em um Pull Request revisável, com critério de aceite verificável.
4. **Provar com um consumidor.** O MVP só termina quando um projeto de exemplo, instalado a partir do pacote, executa de ponta a ponta.
5. **Core pequeno.** Tudo o que não é transversal fica fora do Core.

---

## 2. Visão geral

| Fase | Objetivo | Pré-requisito | Saída |
|---|---|---|---|
| 0 | Recuperar o repositório e completar o diagnóstico | Acesso à pasta de origem ou ao remoto | Clone íntegro, auditoria complementar, D-00 a D-02 decididas |
| 1 | Fundação de governança | Fase 0 | Repositórios coerentes com a decisão, CI e proteção de `main` verificáveis |
| 2 | Decisões e contratos do Core | Fase 1 | ADRs e RFCs aceitos; arquitetura sem ambiguidades |
| 3 | MVP técnico: `orchestrator-core` 0.1.0 | Fase 2 | Runtime funcional, testado, empacotado, com consumidor de exemplo |
| 4 | Primeira Capability e primeiro Provider | Fase 3 | Extensibilidade provada sem alterar o Core |
| 5 | Distribuição e releases | Fase 4 | Pacotes consumíveis, compatibilidade declarada |
| 6 | Evolução futura | Core 1.0 | Fora do escopo inicial |

Situação em 2026-11-11: a Fase 0 está **parcialmente executada**. O diagnóstico inicial e a auditoria do código (E0.3) estão concluídos. A recuperação do Git (E0.1) e a verificação do remoto (E0.4) continuam pendentes.

---

## 3. Fase 0 — Recuperação e diagnóstico complementar

| ID | Entrega | Depende de | Critério de aceite |
|---|---|---|---|
| E0.0 | Cópia de segurança da pasta inteira | — | Cópia feita antes de qualquer reparo; inclui os 21 arquivos alterados depois do commit `6232d68` e nunca commitados |
| E0.1 | Clone íntegro do repositório | Pasta de origem (`C:\Users\guilherme.machado\orchestrator`, segundo `.venv/pyvenv.cfg`) ou acesso ao remoto | `git fsck --full` sem erros; `git status` funciona; o commit `6232d68` existe e a sua árvore é `b1e2d42…`; a pasta atual é preservada até a validação |
| E0.1b | Trabalho não versionado commitado em branch de referência (por exemplo `experiment/scaffold-2026-07`) | E0.0, E0.1 | `git status` limpo; nenhum dos arquivos do Apêndice A do relatório do código ficou de fora |
| E0.2 | Alterações da auditoria em branch `fix/initial-audit-baseline`, com Pull Request | E0.1 | Diffs comparados com o `main` atual, sem sobrescrever arquivos; PR com objetivo, motivação, evidências e impacto |
| E0.3 | Auditoria complementar do código: Core, pacote SQL, testes, CI e templates | Código acessível | **Concluída em 2026-11-11:** `docs/audit/CODE_AUDIT.md`. Pytest, Ruff e MyPy executados; roteiro da seção 8.4 cumprido. Não executado: caminhos com SQLAlchemy e SQL Server, Windows e Python 3.11 |
| E0.4 | Verificação do remoto e dos controles do GitHub | Acesso ao remoto | Lista do que está habilitado; PRs abertos e branches residuais identificados |
| E0.5 | Decisões D-00, D-01, D-02 e D-23 | E0.3 | ADRs aceitos. D-00 já tem recomendação fundamentada: arquivar o scaffold e reconstruir |

**Se a recuperação do Git falhar** (nem origem nem remoto disponíveis): criar um repositório novo a partir da pasta atual, registrando no primeiro commit que o histórico anterior não foi recuperado.

**Portão de saída:** E0.1, E0.1b e E0.5 concluídas.

---

## 4. Fase 1 — Fundação de governança

| ID | Entrega | Depende de | Critério de aceite |
|---|---|---|---|
| E1.1 | Aplicação de D-01 | D-01 | Com a alternativa recomendada: este repositório sem pacote Python; Core em `orchestrator-core`, com histórico preservado. A criação de repositório remoto exige autorização |
| E1.2 | Higiene de branches e de arquivos | E0.1, D-24 | `feature`, `feature-core` e `teste` renomeadas ou removidas; é possível criar `feature/*`; `egg-info` fora do versionamento; `src/orchestrator_core/stage.py` removido; duplicatas `*-1.md` apagadas; `.venv` recriado nesta máquina; `.gitattributes` presente |
| E1.3 | Estrutura documental | D-23, D-24 | Um único local para ADRs (`docs/adr/`, com o modelo existente) e índice; `docs/rfc/`; links de `ISSUE_TEMPLATE/config.yml` e donos em `CODEOWNERS` corrigidos (GOV-05); README com status e estrutura reais; CHANGELOG com seções por tipo e registro retroativo; CONTRIBUTING alinhado a GOVERNANCE; SECURITY com canal de reporte; `ROADMAP.md` como resumo que aponta para este documento; `CLAUDE.md` e documentos do kit incorporados; verificação automática dos caminhos citados na documentação |
| E1.4 | Base de qualidade no repositório de código | D-17, D-18 | `pyproject.toml` com Ruff, MyPy em modo estrito, Pytest e grupos de dependência; lockfile versionado; um comando documentado executa lint, formatação, tipos e testes |
| E1.5 | CI e proteção de `main` | D-19, E1.4 | Um PR de teste é bloqueado sem os checks; matriz de versões e sistemas aprovada; ações fixadas por SHA; permissões mínimas; Dependabot agrupado |
| E1.6 | Triagem dos PRs do Dependabot | E0.4, D-01 | PRs abertos resolvidos ou fechados com justificativa |

**Testes desta fase:** execução real dos workflows; tentativa de push direto em `main` rejeitada; tentativa de merge sem checks rejeitada.

**Portão de saída:** uma mudança qualquer percorre branch, PR, checks e merge sem exceções manuais.

---

## 5. Fase 2 — Decisões e contratos do Core

Nenhum código de produção é escrito nesta fase.

| ID | Entrega | Depende de | Critério de aceite |
|---|---|---|---|
| E2.1 | ADRs de D-03, D-04 e D-05 | Fase 1 | Aceitos |
| E2.2 | RFC-0001: lifecycle, pipeline, contexto, eventos e estágios de borda (D-06, D-07, D-13, D-15, D-16) | E2.1 | Aceita; inclui a tabela de comportamento em falha, cancelamento e timeout |
| E2.3 | ADRs de D-08, D-09, D-10, D-12 e D-14 | E2.1 | Aceitos |
| E2.4 | Protótipo descartável em branch `experiment/*`, com um consumidor de exemplo, para validar a ergonomia de E2.2 e de D-02 | E2.2 | Achados registrados na RFC antes do aceite; o protótipo não é mesclado |
| E2.5 | RFC-0002: escopo do MVP e superfície pública (D-20) | E2.1 a E2.4 | Aceita; lista nominal do que é público |
| E2.6 | ARCHITECTURE e SECURITY atualizados | E2.1 a E2.5 | Ambiguidades DOC-05 e DOC-06 eliminadas; lifecycle documentado igual ao decidido |

Decisões relacionadas e tomadas juntas podem ser registradas em um único ADR. O objetivo é rastreabilidade, não volume de documentos.

O que pode ser reaproveitado do scaffold está na seção 11 de `docs/audit/CODE_AUDIT.md`.

**Portão de saída:** E2.5 aceita.

---

## 6. Fase 3 — MVP técnico: `orchestrator-core` 0.1.0

Esta fase pressupõe a alternativa B de D-00 (reconstruir). Se a decisão for adotar o scaffold, ela é substituída pelo backlog de correções da seção 12 de `docs/audit/CODE_AUDIT.md`, na ordem ali indicada, com um teste de regressão por correção.

### 6.1 Escopo incluído

- Superfície pública pequena e documentada, usada como biblioteca Python.
- Runtime com pipeline extensível e os 8 estágios documentados.
- Execution Context por execução.
- Configuração validada, com precedência definida.
- Composição explícita de dependências.
- Contrato de Capability e registry com registro explícito.
- Tratamento de falhas com teardown garantido.
- Logging com contexto e redação; eventos de lifecycle; port de métricas.
- Retry como utilitário de uso explícito; cancelamento e prazo cooperativos.
- Módulo de apoio a testes, com implementações em memória.
- Projeto consumidor de exemplo.
- Empacotamento e instalação reproduzíveis.

### 6.2 Escopo excluído

Runtime assíncrono; descoberta automática de plugins; interpretador de specs e CLI; persistência de histórico; qualquer Capability ou Provider real; integração com OpenTelemetry; checkpoint, retomada e pausa; tudo o que está na Fase 6.

### 6.3 Entregas

| ID | Entrega | Depende de | Critério de aceite | Testes |
|---|---|---|---|---|
| M1 | Esqueleto do pacote: layout `src/`, `py.typed`, versão em um único lugar, CI | Fase 2 | Wheel e sdist construídos; o wheel instala em ambiente limpo; `import orchestrator_core` funciona em Windows e Linux | Teste de instalação e importação no CI |
| M2 | Hierarquia de erros, `ExecutionContext`, `ExecutionResult` | M1 | Contratos conforme RFC-0001; MyPy estrito sem erros | Imutabilidade; dois contextos não compartilham estado |
| M3 | `Stage`, pipeline e lifecycle padrão | M2 | Comportamento idêntico à tabela da RFC-0001; estágios adicionais podem ser inseridos sem alterar os existentes | Matriz de falha: falha injetada em cada um dos 8 estágios, com verificação dos estágios executados; agregação de erros de teardown; Shutdown idempotente |
| M4 | Configuração e segredos | M2 | Precedência conforme D-08; erro de configuração identifica a chave | Tabela de precedência; um valor-sentinela de segredo não aparece em logs, em `repr` nem em eventos |
| M5 | Contrato de Capability, registry, escopo de recursos | M3 | Registro explícito; duplicidade é erro; recursos liberados em ordem inversa | Capability falsa; falha na aquisição de recurso; liberação parcial |
| M6 | Logging, eventos e métricas | M3, M4 | Toda linha de log de uma execução carrega o seu identificador; handler de evento com falha não interrompe o pipeline | Correlação; isolamento de falha de handler; port de métricas sem implementação não gera erro |
| M7 | Retry, cancelamento e prazo | M3 | Sem retry por padrão; cancelamento leva ao teardown e ao status correto | Relógio falso, sem espera real; testes determinísticos |
| M8 | Fachada pública, documentação de API, módulo de apoio a testes | M2 a M7 | Somente os nomes listados na RFC-0002 são exportados; cada um tem docstring e exemplo | Teste de arquitetura: o Core importa apenas biblioteca padrão e dependências aprovadas; teste da lista de nomes públicos |
| M9 | Projeto consumidor de exemplo | M8 | Projeto com `pyproject.toml` próprio, instalado a partir do wheel, executa de ponta a ponta | Teste de integração no CI, em Windows e Linux |
| M10 | Preparação da release 0.1.0 | M9 | CHANGELOG e notas de release; tag; dois builds consecutivos produzem o mesmo artefato; Definition of Done completa | Verificação de hash dos artefatos; instalação a partir do artefato final |

Ordem: M1 → M2 → M3 → M4 e M5 em paralelo → M6 → M7 → M8 → M9 → M10.

### 6.4 Critérios de aceite do MVP

1. O wheel instala em ambiente limpo, em Windows e Linux, nas versões de Python suportadas.
2. O exemplo de consumidor executa de ponta a ponta usando apenas a superfície pública.
3. O conjunto de dependências de execução do Core é exatamente o aprovado em D-04, verificado por teste.
4. Para falha em qualquer estágio, o teardown executa e o erro original é preservado.
5. Execuções sucessivas e paralelas não compartilham contexto, estado nem recursos (teste de estresse com execuções em sequência e em threads).
6. Nenhum valor de segredo aparece em logs ou eventos.
7. `ruff check`, `ruff format --check`, `mypy` estrito e `pytest` aprovados no CI; meta de cobertura definida na RFC-0002.
8. Documentação de API, README, CHANGELOG e ADRs atualizados.

Publicar o pacote não faz parte do aceite e exige autorização explícita.

---

## 7. Fase 4 — Primeira Capability e primeiro Provider

**Objetivo:** provar que uma tecnologia nova entra sem alteração do Core.

A escolha deve seguir a necessidade do primeiro projeto consumidor real. Na falta dessa informação, a avaliação é:

| Candidata | Dependências | Complexidade | O que prova |
|---|---|---|---|
| SQL com Provider SQLite | Nenhuma além da biblioteca padrão | Média | Separação entre Capability e Provider; um segundo Provider (PostgreSQL) prova a substituição |
| Filesystem com Provider local | Nenhuma | Baixa | Controles de caminho; a substituição só é provada com um segundo Provider |
| HTTP | Biblioteca cliente de terceiros | Média | Timeout e retry em operação real |
| Excel | Biblioteca de terceiros ou automação nativa do Windows | Média a alta | Pouco sobre o desenho; forte dependência de plataforma |
| Browser | Framework de automação e binários de navegador | Alta | Exercita o estágio Provision Dependencies; cedo demais para a primeira prova |

**Recomendação:** `orchestrator-sql` (Capability, com consultas sempre parametrizadas) e `orchestrator-sqlite` (Provider sobre a biblioteca padrão). O pacote SQL do scaffold serve de referência para o mapeamento de tipos e a geração de DDL, sem as convenções de fila (D-25) e sem montagem de SQL a partir de texto não validado (SQL-02).

| ID | Entrega | Critério de aceite |
|---|---|---|
| E4.1 | RFC da Capability escolhida | Aceita; contrato funcional e port do Provider definidos; regra de validação de identificadores definida; nenhuma convenção de consumidor no pacote |
| E4.2 | Pacote da Capability | Depende apenas do Core; suíte de conformidade aprovada |
| E4.3 | Pacote do Provider | Depende da Capability; exceções de infraestrutura traduzidas; testes com o serviço real quando disponível |
| E4.4 | Segundo Provider para a mesma Capability | Troca de Provider no exemplo de consumidor apenas por configuração |
| E4.5 | Verificação de extensibilidade | Nenhum commit no Core foi necessário; se foi, o motivo vira ADR |

---

## 8. Fase 5 — Distribuição e releases

- Canal de publicação definido (D-20) e publicação automatizada.
- Notas de release e guias de migração.
- Matriz de compatibilidade entre Core, Capabilities e Providers, testada no CI (D-11).
- Análise de dependências e de licenças; SBOM e proveniência conforme a maturidade.
- Modelos de repositório para novas Capabilities e Providers.
- Política de suporte e de depreciação aplicada à primeira versão retirada.

---

## 9. Fase 6 — Evolução futura

Execução distribuída, agentes remotos, execução em nuvem, marketplace de plugins, registry de pacotes, dashboards, workflow engine, scheduling e automação assistida por IA. Cada item exige RFC com caso de uso real e não deve aumentar o Core (D-22).

---

## 10. Decisões que bloqueiam cada fase

| Fase | Decisões necessárias |
|---|---|
| 0 → 1 | D-00, D-01, D-02, D-23 |
| 1 | D-17, D-18, D-19, D-24 |
| 2 | D-03 a D-10, D-12 a D-16, D-20 |
| 3 | Todas as da Fase 2 aceitas |
| 4 | D-11, D-21, D-25 e a RFC da Capability |
| 5 | D-20 (canal de publicação) |

---

## 11. Fora do escopo inicial

- Qualquer item da Fase 6.
- Mais de uma Capability antes de a primeira estar concluída.
- Providers de nuvem.
- Interface gráfica, API HTTP e serviço em execução contínua.
- Instalação de pacotes em tempo de execução.
- Compatibilidade com versões de Python anteriores à decidida em D-17.

---

## 12. Riscos do plano

| Risco | Efeito | Mitigação |
|---|---|---|
| Trabalho não versionado perdido antes da recuperação do Git | Perda de 21 arquivos alterados depois do último commit | Cópia de segurança imediata (E0.0); nenhum reparo do Git na pasta sem cópia |
| Histórico do Git não recuperável | Perda do histórico; o código atual permanece | Procurar a pasta de origem; em último caso, repositório novo a partir da pasta atual |
| `main` remoto à frente do retrato local | Correções desta sessão conflitam com mudanças posteriores | Comparar em vez de sobrescrever (E0.2) |
| Volume de decisões antes do primeiro código | Atraso e perda de ritmo | Agrupar decisões relacionadas; validar com protótipo descartável (E2.4) |
| Mantenedor único | A exigência de revisão aprovada não pode ser cumprida pelo próprio autor do PR | Definir em D-19 quantas aprovações são exigidas e quem revisa |
| Controles de segurança indisponíveis no plano atual | Política declarada e não aplicável | Decidir em D-19 entre repositório público, contratação ou lacuna registrada |
| Contratos errados congelados cedo | Quebra de compatibilidade logo após a 0.1.0 | Antes da 1.0, versão menor pode quebrar; exemplo de consumidor e suíte de conformidade como detectores |
| Crescimento do Core por conveniência | Perda do principal atributo de qualidade | Teste de arquitetura sobre imports; todo port novo no Core exige ADR |

---

## 13. Próxima ação

1. Fazer a cópia de segurança da pasta (E0.0).
2. Recuperar o Git a partir da pasta de origem ou do remoto e commitar o trabalho não versionado (E0.1, E0.1b).
3. Decidir D-00, D-01 e D-02.

Nenhuma implementação do Core deve começar antes desses três passos.
