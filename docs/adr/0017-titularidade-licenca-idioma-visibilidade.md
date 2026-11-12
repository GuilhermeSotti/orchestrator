# ADR-0017 — Titularidade, licença, idioma e visibilidade

| Campo | Valor |
|---|---|
| Status | Aceito |
| Data | 2026-11-12 |
| Decisão | D-23 |
| Decisor | Claude, por delegação explícita do responsável pelo projeto (2026-11-12) |

## Contexto

Havia identidades divergentes (GOV-02): remoto numa conta corporativa, commits com e-mail corporativo, LICENSE em nome de pessoa física e autor do pacote com e-mail pessoal. O idioma da documentação era misto (DOC-07).

## Decisão

1. **Licença**: MIT, como está. O arquivo `LICENSE` não foi alterado e é copiado para cada pacote.
2. **Autoria nos metadados**: `Orchestrator Contributors`, sem nome ou e-mail pessoal nos pacotes.
3. **Titularidade jurídica** (projeto pessoal ou da empresa, titular do copyright): não é uma decisão técnica e não foi tomada aqui. Fica registrada como pendência do responsável. Esta documentação não constitui avaliação jurídica.
4. **Nome do repositório**: `orchestrator` (ADR-0001).
5. **Idioma**:
   - documentação narrativa (README, ADRs, RFCs, guias, changelogs, templates do GitHub) em português do Brasil;
   - código em inglês: identificadores, docstrings, mensagens de exceção e de log, metadados dos pacotes;
   - mensagens de commit: tipo e escopo do Conventional Commits em inglês, descrição em português.
6. **Visibilidade** (privado ou público): decisão do responsável, com efeito nos controles do GitHub (ADR-0014). Nada nesta entrega depende dela.

## Consequências

- Dados pessoais não entram em metadados publicáveis.

## Referências

- `LICENSE`; ADR-0014; ADR-0018.
