# ADR-0012 — Versões de Python e plataformas

| Campo | Valor |
|---|---|
| Status | Aceito |
| Data | 2026-11-12 |
| Decisão | D-17 |
| Decisor | Claude, por delegação explícita do responsável pelo projeto (2026-11-12) |

## Contexto

ARCHITECTURE indicava Python 3.13+; o `pyproject.toml` do scaffold declarava `>=3.11` (PKG-02); a CI usava 3.11 (CI-01).

## Decisão

1. Todos os pacotes declaram `requires-python = ">=3.13"`, sem limite superior. O código usa recursos de 3.12 e 3.13 (parâmetros de tipo da PEP 695, `typing.Self`, `sqlite3.connect(autocommit=...)`).
2. A CI testa Python 3.13, 3.14 e 3.15 (lançada em 9 de outubro de 2026) em Ubuntu e Windows. Cada versão nova entra na matriz quando for lançada.
3. Plataformas suportadas: Windows e Linux. macOS não é testado nem bloqueado.

## Consequências

- A validação local desta entrega foi feita em Linux com Python 3.13.18. Windows, Python 3.14 e Python 3.15 dependem da primeira execução da CI.
- Um consumidor preso a uma versão anterior exige nova decisão; manter compatibilidade abaixo de 3.13 custaria os recursos acima.

## Referências

- `.github/workflows/ci.yml`.
