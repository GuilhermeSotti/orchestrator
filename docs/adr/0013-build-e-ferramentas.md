# ADR-0013 — Build, ferramentas de desenvolvimento e versões fixadas

| Campo | Valor |
|---|---|
| Status | Aceito |
| Data | 2026-11-12 |
| Decisão | D-18 |
| Decisor | Claude, por delegação explícita do responsável pelo projeto (2026-11-12) |

## Contexto

Havia duas fontes de verdade divergentes (`pyproject.toml` e `requirements.txt`), nenhum lockfile, Ruff e MyPy não declarados (PKG-03) e licença em formato depreciado (PKG-04).

## Decisão

1. **Backend**: setuptools (`setuptools>=77`) em cada pacote, licença como expressão SPDX (`license = "MIT"`) e `license-files`.
2. **Versão em um único lugar**: `src/<pacote>/_version.py`, lida pelo setuptools (`dynamic = ["version"]`) e exportada como `__version__`.
3. **Ferramentas de desenvolvimento** com versões exatas em `requirements/dev.txt`, única fonte para desenvolvimento local e CI. Configuração de Ruff, MyPy, Pytest e coverage no `pyproject.toml` da raiz, que não é pacote.
4. **Grupos de dependência (PEP 735)** não são usados por enquanto: um arquivo de requisitos funciona com qualquer `pip` e com o Dependabot.
5. **Lockfile com hashes**: pendente. As versões foram fixadas e verificadas no ambiente desta entrega, que não tinha acesso ao índice de pacotes para calcular hashes. Próximo passo: gerar `requirements/dev.lock` com `pip-compile --generate-hashes` (ou `uv pip compile --generate-hashes`) e instalar com `--require-hashes`.
6. **Build reproduzível**: `tools/build_packages.py` constrói wheel e sdist de cada pacote com `SOURCE_DATE_EPOCH` fixo e, com `--check`, constrói duas vezes e compara os hashes SHA-256.

## Alternativas consideradas

- **hatchling, flit-core, uv_build.** Trocar de backend não resolve nenhum problema atual.
- **Poetry ou PDM.** Introduzem uma ferramenta obrigatória para todos os contribuidores.
- **uv com lockfile.** Boa opção futura; adotar uma ferramenta nova é mudança para outra ADR.

## Consequências

- Nenhum pacote tem dependência de terceiros em tempo de execução; o lock só afeta ferramentas de desenvolvimento.

## Referências

- `requirements/dev.txt`, `tools/build_packages.py`.
