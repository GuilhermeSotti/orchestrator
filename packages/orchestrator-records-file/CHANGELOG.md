# Changelog — orchestrator-records-file

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/). Versionamento semântico; antes da 1.0, uma versão menor pode quebrar compatibilidade.

## [Não lançado]

Versão 0.1.0 preparada em 2026-11-15 na branch local `feature/records-file`, sem push, tag nem release. Depende do `orchestrator-core` 0.2.

### Adicionado

- `JsonLinesRecordSink`: registros de execução em JSON Lines, um arquivo por dia e por processo, retenção opcional por dias e `fsync` opcional ([RFC-0009](../../docs/rfc/0009-destinos-de-registros-e-logs.md), seção 2.2).
- `TextLogHandler`: logs técnicos em TXT organizados por estágio, subetapa e data, um arquivo por processo, retenção padrão de 6 meses, mascaramento e correlação do Core (RFC-0009, resposta 1).
- Teste com quatro processos reais gravando ao mesmo tempo nas mesmas pastas (resposta 5).
