## Objetivo

O que muda, em uma ou duas frases.

## Motivação

Problema resolvido ou oportunidade atendida. Issue relacionada: #

## Impacto

- Pacotes afetados:
- Muda contrato público? Se sim, RFC-0002, CHANGELOG e compatibilidade foram atualizados:
- ADR ou RFC relacionada:

## Evidência de testes

Comandos executados e resultado.

```text
ruff check . && ruff format --check . && mypy && pytest
```

## Checklist (Definition of Done)

- [ ] Type hints e docstrings completos
- [ ] Testes novos ou ajustados; correção de bug com teste de regressão
- [ ] Ruff, formatação, MyPy e Pytest passando localmente
- [ ] Documentação e CHANGELOG do pacote atualizados
- [ ] Nenhum segredo, dado pessoal ou credencial no diff
- [ ] Dependência nova justificada (no Core, nenhuma)
