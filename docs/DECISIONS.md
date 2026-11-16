# Registro de decisões — Orchestrator

| Campo | Valor |
|---|---|
| Atualizado em | 2026-11-15 |
| Situação | As 26 decisões levantadas pelas auditorias (D-00 a D-25) foram tomadas em 2026-11-12, por delegação explícita do responsável pelo projeto, e registradas em ADRs e RFCs. Em 2026-11-15 o responsável respondeu às perguntas das RFCs 0004 a 0012 (seção 3) e tomou quatro decisões de encaminhamento (seção 4). Ainda em 2026-11-15 o responsável aceitou as RFCs 0004 a 0012 (seção 5); as RFCs 0013 e 0014 continuam em proposta |
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

Situação conferida em 2026-11-15 pelos arquivos de `.git` da pasta do responsável e pelas páginas públicas do repositório ([reconciliação](audit/RFC_RESPONSE_RECONCILIATION.md), seção 1).

| # | Pendência | Situação em 2026-11-15 |
|---:|---|---|
| 1 | Recuperar o acesso ao remoto e reconciliar o histórico ([guia](guides/recuperacao-do-historico.md)) | Acesso recuperado: `e8eaabe` foi enviado em 2026-11-13 e os PRs #1 e #2 foram integrados no GitHub. `main` remoto tem 15 commits e não contém os de julho; o estado de julho continua na tag `archive/scaffold-2026-07`. Falta confirmar que a substituição do histórico remoto foi intencional |
| 2 | Aplicar a proteção de `main` e verificar os controles do plano ([guia](guides/governanca-github.md)) | Não verificável sem acesso administrativo; continua pendente |
| 3 | Habilitar o reporte privado de vulnerabilidades (`SECURITY.md`) | Não verificado |
| 4 | Titularidade jurídica e visibilidade (ADR-0017) | O repositório está público; a titularidade continua pendente |
| 5 | Remover as branches `feature`, `feature-core` e `teste` do remoto (ADR-0018) | Não aparecem mais no remoto. Resta `dependabot/pip/requirements/dev-tools-ff8c5acc02`, do PR #2 já integrado |
| 6 | Merge por squash (ADR-0018) | Os PRs #1 e #2 entraram com merge commit; permitir só squash nas configurações do repositório |
| 7 | Aceite formal das partes implementadas (RFC-0005, 2.1 a 2.4; RFC-0006, 2.1; RFC-0007, resposta 6; RFC-0009, resposta 6) ou exceção de governança registrada | Resolvida em 2026-11-15: as RFCs 0005, 0006, 0007 e 0009 foram aceitas (seção 5). A implementação veio antes do aceite (`GOVERNANCE.md`, seção 5); o aceite regulariza essa ordem para a 0.2.0 |
| 8 | Atualizar a `main` local e importar a integração da 0.2.0 | Em 2026-11-15, 15h56, a pasta continuava em `e8eaabe`, quatro commits atrás de `origin/main` (`564dd24`). A branch local `feature/core-0.2`, a partir de `564dd24`, chegou à pasta num bundle; procedimento na [consolidação](audit/CORE_020_CONSOLIDATION.md), seção 8 |
| 9 | Autorizar push das branches locais e abertura dos PRs: `feature/core-0.2` (Core, SQL e SQLite 0.2.0, um PR, ADR-0009) e, em pilha sobre ela, `feature/notifications`, `feature/notifications-smtp`, `feature/notifications-teams`, `feature/records-file` e `feature/calendar` (um pacote por PR, RFC-0004) | Pendente. Nenhum push, PR, merge, tag ou release foi feito. Procedimento de importação na pasta: [consolidação](audit/CORE_020_CONSOLIDATION.md), seção 10.2 |

## 3. Respostas do responsável às RFCs 0004 a 0012 (2026-11-15)

Decisões explícitas, gravadas pelo responsável nas próprias RFCs. Quando foram dadas, não equivaliam ao aceite das RFCs (instrução de 2026-11-15); o aceite veio depois e está na seção 5. Não recebem número D-NN: os números a partir de D-26 ficam para as decisões da RFC-0004, seção 4, ainda não transcritas. Classificação completa, conflitos e lacunas: [reconciliação](audit/RFC_RESPONSE_RECONCILIATION.md).

| Origem | Decisão do responsável | Efeito em 2026-11-15 |
|---|---|---|
| RFC-0005, 1 | `teardown_timeout` parametrizável; padrão de 60 s; zero desliga o limite | Implementado no Core 0.2.0 |
| RFC-0005, 2 | Limite de subetapas parametrizável, padrão de 1.000; aninhamento desde a primeira versão | Implementado |
| RFC-0005, 3 | Subetapas sempre no registro da execução; haverá subetapas padrão da plataforma | Registro implementado; subetapas padrão: opção C (seção 4, DE-2), com proposta na [RFC-0014](rfc/0014-subetapas-padrao-de-finalizacao.md) |
| RFC-0005, 4 | Toda automação passa pelo evento Finished na finalização | Garantido nos encerramentos cooperativos; guia de sinais |
| RFC-0006, 1 a 3 | Cofre, identidade e acesso de rede parametrizáveis; cache limitado à execução | Para o Provider de cofre (bloqueado) |
| RFC-0006, 5 | Opção A: `connect(secrets)` | Implementado no SQL e no SQLite 0.2.0 |
| RFC-0007, 2 a 6 | Destinatários e eventos parametrizáveis; PT-BR formal; sem limite nem agrupamento; `required` parametrizável durante a execução; lista de estágios no contexto | Lista de estágios implementada; o resto, para a Capability (bloqueada) |
| RFC-0008, 2, 5 a 8 | Funções de inserção na Capability; 3 tentativas por padrão; recuperação manual, sem lease; conclusão atômica com o negócio; encerrar em falha definitiva de subetapa essencial | Para a Capability de fila (bloqueada) |
| RFC-0009, 1, 5, 6 | Retenção padrão de 6 meses; estrutura de pastas em TXT; vários processos na mesma pasta; falha do registro ignorada | Falha do registro implementada no Core 0.2.0; o resto, bloqueado |
| RFC-0010, 1, 2, 5 a 7 | Localização de elementos de interface; um arquivo compartilhado por sistema, mantido à mão; sempre a versão mais atual; sem fixar versão; busca pelo nome padronizado | Contrato a refazer (bloqueado) |
| RFC-0011, 1, 6, 7 | Feriados cadastrados manualmente; sábado e domingo como dias úteis (a confirmar); fuso da máquina | Para a Capability de calendário (bloqueada) |
| RFC-0012, 2, 4 | Autenticação interativa (usuário, senha, mapeamentos com override) e por token; segundo fator parametrizável | Condicional a um sistema real |
| RFC-0004, 2 e 10 | Credenciais de banco parametrizáveis por automação; recursos compartilhados por todos os projetos | Orientação geral |

## 4. Decisões de encaminhamento do responsável (2026-11-15)

Decisões expressas do responsável na instrução de 2026-11-15, 15h56, sobre o que fazer a seguir. Não são aceite de RFC nem ADR e não recebem número D-NN. Quando foram tomadas, as RFCs 0004 a 0014 estavam em "Proposta. Não aceita"; as RFCs 0004 a 0012 foram aceitas depois (seção 5), e as RFCs 0013 e 0014 continuam em proposta. Nenhuma ADR foi criada ou alterada.

| # | Data | Decisão | Escopo | Situação | Efeito registrado |
|---|---|---|---|---|---|
| DE-1 | 2026-11-15 | Aprovação integral das implementações 0.2.0 de `orchestrator-core`, `orchestrator-sql` e `orchestrator-sqlite` | Código, testes e documentação da entrega de 2026-11-15 ([reconciliação](audit/RFC_RESPONSE_RECONCILIATION.md), seção 7). As duas correções da consolidação são posteriores e seguem para revisão no PR ([consolidação](audit/CORE_020_CONSOLIDATION.md), seção 4) | Aprovada como encaminhamento; as RFCs de origem não foram aceitas | Consolidação e preparação da integração; o merge ainda depende da pendência 7 (seção 2) |
| DE-2 | 2026-11-15 | Subetapas padrão: opção C | Contemplar a finalização do ciclo de vida e a finalização de sistemas e processos ([reconciliação](audit/RFC_RESPONSE_RECONCILIATION.md), seção 8, item 2) | Direção aprovada; proposta técnica em proposta | [RFC-0014](rfc/0014-subetapas-padrao-de-finalizacao.md). Nada implementado; encerramento de processos de terceiros continua vedado sem contrato e autorização |
| DE-3 | 2026-11-15 | Segredos em SQL: elaborar uma RFC de segurança específica, sem implementar | Conflito C4 da reconciliação | Direção aprovada; RFC em proposta | [RFC-0013](rfc/0013-segredos-em-sql-avaliacao-de-seguranca.md). Nenhum armazenamento de valores nem cifra implementados |
| DE-4 | 2026-11-15 | Próximo passo: consolidar o Core 0.2.0 e preparar a sua integração | Core, SQL e SQLite 0.2.0 | Executada até o limite autorizado: branch e commits locais, sem push nem PR | [Consolidação](audit/CORE_020_CONSOLIDATION.md); pendências 7 a 9 (seção 2) |

## 5. Aceite de RFCs (2026-11-15)

O responsável aceitou as RFCs 0004 a 0012 em 2026-11-15, marcando "Aceita" no cabeçalho de cada uma, e confirmou o aceite na sessão de trabalho do mesmo dia. As RFCs 0013 e 0014 continuam "Proposta. Não aceita" até aceite formal.

| Campo | Registro |
|---|---|
| Data | 2026-11-15 |
| Responsável | Proprietário do projeto |
| Decisão | "Todos os RFCs do repositório estão formalmente aceitos, exceto RFC-0013 e RFC-0014" (instrução de 2026-11-15, 20h16, reenviada às 22h21) |
| Escopo | Todas as RFCs ativas, exceto 0013 e 0014: as RFCs 0004 a 0012 passaram a "Aceita"; as RFCs 0001 a 0003 já estavam aceitas e implementadas na 0.1.0 e mantêm o histórico. Não há RFC rejeitada, substituída ou obsoleta no repositório |
| Consequência | Autorização para implementar as RFCs aceitas, dentro de escopos, condições, dependências e critérios de aceite. Não autoriza push, PR, merge, tag, release nem publicação (pendência 9) |
| Restrições | Respeitar dependências entre entregas, decisões vigentes (ADRs; D-28 para dependências de terceiros), segurança e questões ainda não especificadas: as entregas que dependem de uma questão aberta da [reconciliação](audit/RFC_RESPONSE_RECONCILIATION.md) continuam bloqueadas por ela (seção 10 da reconciliação). Nada que dependa só das RFCs 0013 e 0014 é implementado |

| RFC | Tema | Observação no aceite |
|---|---|---|
| [0004](rfc/0004-controles-reutilizaveis-escopo-e-sequencia.md) | Controles reutilizáveis: escopo e sequência | — |
| [0005](rfc/0005-core-0-2-subetapas-mascaramento-teardown-e-sinais.md) | Core 0.2: mascaramento, teardown, subetapas e sinais | Regulariza as partes 2.1 a 2.4 implementadas (DE-1) |
| [0006](rfc/0006-segredos-cofres-e-credenciais-de-providers.md) | Segredos: cofres e credenciais de Providers | Regulariza a parte 2.1 implementada (DE-1); valores de segredos em SQL seguem na RFC-0013, em proposta |
| [0007](rfc/0007-capability-de-notificacoes.md) | Capability de notificações | Regulariza a resposta 6 implementada (DE-1) |
| [0008](rfc/0008-capability-de-fila.md) | Capability de fila | — |
| [0009](rfc/0009-destinos-de-registros-e-logs.md) | Destinos de registros e logs | Regulariza a resposta 6 implementada (DE-1) |
| [0010](rfc/0010-mapeamentos-compartilhados.md) | Mapeamentos compartilhados | — |
| [0011](rfc/0011-calendarios-e-dias-uteis.md) | Calendários e dias úteis | — |
| [0012](rfc/0012-autenticacao-por-sistema.md) | Autenticação por sistema | Pedido do responsável: criar um caso de exemplo com mapeamentos simples usando o Google |

O aceite não resolve sozinho os conflitos e lacunas da [reconciliação](audit/RFC_RESPONSE_RECONCILIATION.md): as entregas que dependem de uma decisão ainda aberta continuam bloqueadas por ela. Os passos de aceite da RFC-0004, seção 9, foram feitos em 2026-11-15: decisões D-26 a D-33 (abaixo), [ADR-0020](adr/0020-provider-sobre-outra-capability.md), `ARCHITECTURE.md` (seção 5) e Fase 7 do roadmap.

### 5.1 Decisões transversais da RFC-0004 (D-26 a D-33)

A RFC-0004, seção 4, pede que, aceita a RFC, cada decisão transversal entre aqui a partir de D-26. O aceite foi feito sem ressalvas a essas decisões; por isso cada uma registra a recomendação da RFC, salvo onde o responsável decidiu outra coisa (indicado). O responsável pode rever qualquer uma por nova decisão.

| ID | Tema | Decisão | Origem |
|---|---|---|---|
| D-26 | DS-1: Provider que usa outra Capability | Permitido, com regras | [ADR-0020](adr/0020-provider-sobre-outra-capability.md) |
| D-27 | DS-2: compatibilidade da API do Core antes da 1.0 | Mantida a igualdade exata (ADR-0009); uma única 0.2 para Core, SQL e SQLite; rever na segunda versão menor ou na primeira separação de pacote | RFC-0004, recomendação (a) |
| D-28 | DS-3: primeiras dependências de terceiros | Os cinco pontos da RFC-0004, seção 4: justificativa no PR; lock com hashes (ADR-0013) como pré-requisito; wheels baixados do lock para o `tools/e2e.py`; matriz de Python completa ou declarada; licença no README. Até o lock existir, nenhum Provider com dependência de terceiros | RFC-0004, recomendação |
| D-29 | DS-4: nomes de pacotes | `orchestrator-<capability>` e `orchestrator-<capability>-<tecnologia>` quando a tecnologia servir a mais de uma Capability; os nomes da RFC-0004, seção 3 | RFC-0004, recomendação |
| D-30 | DS-5: fronteira com a ADR-0016 | Rastrear partes executadas pelo código do consumidor entra; compor (a plataforma decidir ordem, repetir, pular ou retomar) continua fora | RFC-0004, recomendação |
| D-31 | DS-6: Excel | Dependência direta do primeiro Provider que usar; Capability só no segundo uso | RFC-0004, recomendação (b) |
| D-32 | DS-7: finalização de processos | **Decidida pelo responsável**: opção C (DE-2, seção 4). Contrato e implementação dependem da RFC-0014, em proposta | DE-2 |
| D-33 | DS-8: primeira entrega | Fatia "aviso de falha" (E7.10 a E7.12), demonstrada num exemplo em `examples/`, porque o responsável pediu uma plataforma genérica, sem automação específica (RFC-0004, resposta 1) | RFC-0004, seção 6 |

## 6. Processo para novas decisões

- Decisão arquitetural: ADR em `docs/adr/`. Funcionalidade grande ou transversal: RFC em `docs/rfc/`, aceita antes da implementação.
- Decisões relacionadas podem dividir o mesmo registro.
- Toda escolha de tecnologia considera manutenção, adoção, segurança, licença e custo operacional.
