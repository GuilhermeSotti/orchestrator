# Contribuindo

Obrigado por contribuir com o Orchestrator. As regras completas estão em [GOVERNANCE.md](GOVERNANCE.md); este guia é o caminho prático.

## Ambiente

Requisitos: Python 3.13 ou superior e Git.

```powershell
py -3.13 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements\dev.txt
python -m pip install -e packages\orchestrator-core -e packages\orchestrator-sql -e packages\orchestrator-sqlite -e examples\hello-automation -e examples\sales-report
```

Em Linux ou macOS, use `python3.13 -m venv .venv` e `source .venv/bin/activate`.

## Verificações

Rode antes de abrir o PR; são as mesmas da CI:

```powershell
ruff check .
ruff format --check .
mypy
pytest
coverage run -m pytest; coverage report        # mínimo de 90%
python tools\build_packages.py --check          # build reproduzível
python -m tools.e2e                             # wheels em ambiente limpo + exemplos
```

## Fluxo

1. Crie uma branch a partir de `main` com um dos prefixos: `feature/`, `fix/`, `hotfix/`, `release/`, `experiment/`, `docs/` ou `chore/`.
2. Faça a menor mudança coesa que resolva o problema, com testes. Correção de bug vem com teste de regressão.
3. Atualize a documentação e o `CHANGELOG.md` do pacote afetado (ou o da raiz, para mudanças do repositório).
4. Use mensagens no padrão Conventional Commits, com descrição em português: `fix(sql): rejeitar parâmetros não usados`.
5. Abra o PR preenchendo o template: objetivo, motivação, evidência de testes, impacto e ADR/RFC relacionadas.
6. Mudança arquitetural significativa precisa de ADR; funcionalidade grande precisa de RFC aceita antes do código.

## Estilo

- Código, docstrings, mensagens de exceção e de log em inglês; documentação narrativa em português.
- Type hints em tudo; MyPy estrito sem erros.
- Docstrings no estilo Google em todo nome público.
- Sem dependências novas sem justificativa; no Core, nenhuma.

## Segurança

Nunca commite segredos. Vulnerabilidades: siga [SECURITY.md](SECURITY.md), sem issue pública.
