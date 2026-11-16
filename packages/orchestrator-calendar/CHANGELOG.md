# Changelog — orchestrator-calendar

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/). Versionamento semântico; antes da 1.0, uma versão menor pode quebrar compatibilidade.

## [Não lançado]

Versão 0.1.0 preparada em 2026-11-15 na branch local `feature/calendar`, sem push, tag nem release. Depende do `orchestrator-core` 0.2.

### Adicionado

- `CalendarCapability`, `Calendars` e `BusinessCalendar`: fim de semana declarado (sem padrão), camadas com precedência, cobertura obrigatória, horizonte mínimo, `explain`, `today` no fuso da máquina e evento `CalendarLoaded` ([RFC-0011](../../docs/rfc/0011-calendarios-e-dias-uteis.md)).
- `CalendarSource` e a fonte embutida `FileCalendarSource` (TOML, CSV e JSON; versão SHA-256 do conteúdo).
- `orchestrator_calendar.testing`: `InMemoryCalendarSource` e a suíte `CalendarSourceContract`.
