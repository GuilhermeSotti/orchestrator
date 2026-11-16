# RFCs

Propostas para funcionalidades grandes ou transversais. Uma RFC é aceita antes da implementação; ao ser implementada, registra a versão que a contém.

| RFC | Título | Status |
|---|---|---|
| [0001](0001-ciclo-de-vida-da-execucao.md) | Ciclo de vida da execução | Aceita, implementada (`orchestrator-core` 0.1.0) |
| [0002](0002-escopo-do-mvp-e-api-publica.md) | Escopo do MVP, API pública e distribuição | Aceita, implementada (`orchestrator-core` 0.1.0) |
| [0003](0003-capability-sql.md) | Capability SQL e Provider SQLite | Aceita, implementada (`orchestrator-sql` e `orchestrator-sqlite` 0.1.0) |
| [0004](0004-controles-reutilizaveis-escopo-e-sequencia.md) | Controles reutilizáveis: escopo, arquitetura modular e sequência de entregas | Aceita em 2026-11-15; perguntas respondidas em 2026-11-15 |
| [0005](0005-core-0-2-subetapas-mascaramento-teardown-e-sinais.md) | Core 0.2: mascaramento público, orçamento de teardown, subetapas e encerramento por sinal | Aceita em 2026-11-15; partes 2.1 a 2.4 implementadas na 0.2.0 (branch local `feature/core-0.2`, sem release); implementação aprovada em 2026-11-15 (DE-1) |
| [0006](0006-segredos-cofres-e-credenciais-de-providers.md) | Segredos: cofres como Providers e credenciais em Providers | Aceita em 2026-11-15; parte 2.1 (opção A) implementada na 0.2.0 e aprovada (DE-1); valores de segredos em SQL avaliados na RFC-0013 |
| [0007](0007-capability-de-notificacoes.md) | Capability de notificações e Providers de e-mail e Teams | Aceita em 2026-11-15; resposta 6 no Core 0.2.0; Capability em `orchestrator-notifications` 0.1.0 (branch local `feature/notifications`); canais SMTP e Teams nas branches `feature/notifications-smtp` e `feature/notifications-teams` |
| [0008](0008-capability-de-fila.md) | Capability de fila e Provider SQL | Aceita em 2026-11-15 |
| [0009](0009-destinos-de-registros-e-logs.md) | Destinos de registros de execução e de logs técnicos | Aceita em 2026-11-15; resposta 6 na 0.2.0 (DE-1); destinos em arquivo (seção 2.2 e resposta 1) em `orchestrator-records-file`, branch local `feature/records-file`; SQL (2.3) bloqueado |
| [0010](0010-mapeamentos-compartilhados.md) | Repositório compartilhado de mapeamentos | Aceita em 2026-11-15 |
| [0011](0011-calendarios-e-dias-uteis.md) | Calendários, feriados e dias úteis | Aceita em 2026-11-15; `orchestrator-calendar` com fonte em arquivo na branch local `feature/calendar` |
| [0012](0012-autenticacao-por-sistema.md) | Reutilização de fluxos de autenticação por sistema | Aceita em 2026-11-15; continua condicional a um caso de uso real |
| [0013](0013-segredos-em-sql-avaliacao-de-seguranca.md) | Valores de segredos em SQL: avaliação de segurança | Proposta, não aceita (2026-11-15); nada implementado |
| [0014](0014-subetapas-padrao-de-finalizacao.md) | Subetapas padrão: finalização do ciclo de vida e de sistemas e processos | Proposta, não aceita (2026-11-15); nada implementado |

As RFCs 0004 a 0012 partem do diagnóstico [docs/audit/SCOPE_DIAGNOSIS.md](../audit/SCOPE_DIAGNOSIS.md). A ordem de leitura sugerida começa pela 0004, que resume as demais. As respostas do responsável estão em cada RFC; a classificação de cada resposta, os conflitos e o que pode avançar estão em [docs/audit/RFC_RESPONSE_RECONCILIATION.md](../audit/RFC_RESPONSE_RECONCILIATION.md). As RFCs 0013 e 0014 atendem às decisões de encaminhamento DE-3 e DE-2 de 2026-11-15 ([DECISIONS](../DECISIONS.md), seção 4). "Aprovada (DE-1)" se refere à implementação; o aceite das RFCs 0004 a 0012 está em [DECISIONS](../DECISIONS.md), seção 5. As RFCs 0013 e 0014 continuam em proposta.

Para propor uma RFC, abra uma issue com o formulário "RFC" e, aceita a discussão, um PR com o documento `NNNN-titulo.md` nesta pasta.
