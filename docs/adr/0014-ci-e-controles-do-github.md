# ADR-0014 — CI e controles do GitHub

| Campo | Valor |
|---|---|
| Status | Aceito |
| Data | 2026-11-12 |
| Decisão | D-19 |
| Decisor | Claude, por delegação explícita do responsável pelo projeto (2026-11-12) |

## Contexto

A CI rodava apenas `pytest` em Python 3.11 (CI-01); as validações descritas em SECURITY não existiam (CI-02). Os controles do GitHub não puderam ser verificados (SEC-01): o remoto exige autenticação que o ambiente desta entrega não tinha.

## Decisão

1. **CI** (`.github/workflows/ci.yml`), com permissão somente de leitura:
   - `quality`: `ruff check`, `ruff format --check`, `mypy` estrito, verificação de links da documentação e testes de fronteira entre pacotes;
   - `tests`: Pytest com cobertura mínima de 90% em Python 3.13, 3.14 e 3.15, Ubuntu e Windows;
   - `build`: wheel e sdist de cada pacote, construídos duas vezes e comparados;
   - `e2e`: `python -m tools.e2e` instala os wheels num ambiente virtual limpo (sem índice de pacotes, sem a árvore de fontes no caminho) e executa os dois exemplos a partir de uma pasta temporária, em Ubuntu e Windows.
2. **Release** (`.github/workflows/release.yml`): ao enviar uma tag `<distribuição>/v<versão>`, constrói o pacote e anexa os artefatos a uma release do GitHub, com `gh`. Não publica em índice de pacotes (RFC-0002).
3. **Ações fixadas por SHA**, com a versão em comentário: `actions/checkout` v7.0.1, `actions/setup-python` v7.0.0 e `actions/upload-artifact` v6.0.0. Os SHAs foram obtidos em 2026-11-12 de links de comparação de PRs do Dependabot e de espelhos públicos dos repositórios das ações, sem consulta à API do GitHub; a primeira execução da CI os valida, e o Dependabot os mantém (há `upload-artifact` v7, cuja atualização fica para o Dependabot).
4. **Dependabot** para GitHub Actions e para `requirements/dev.txt`, semanal e agrupado.
5. **Análise estática de segurança** no CI pelas regras `S` do Ruff (as mesmas do Bandit). CodeQL pela configuração padrão do GitHub (sem arquivo de workflow), onde o plano permitir.
6. **Proteção de `main`** (configuração do repositório, ação do responsável): PR obrigatório, checks `quality`, `tests`, `build` e `e2e` obrigatórios, histórico linear, sem push forçado nem exclusão. Passo a passo em `docs/guides/governanca-github.md`.
7. **Revisão com mantenedor único**: enquanto houver um só mantenedor, o PR é obrigatório, mas a aprovação de outra pessoa não é exigida (o autor de um PR não pode aprová-lo). Com o segundo mantenedor, passa a exigir uma aprovação.

## Pendente do responsável (não executável daqui)

- Aplicar a proteção de `main` e verificar o plano: em repositório privado, secret scanning, push protection, code scanning e dependency review dependem de GitHub Secret Protection e GitHub Code Security (planos Team e Enterprise); em repositório público são gratuitos.
- Habilitar o reporte privado de vulnerabilidades (canal citado em SECURITY).

## Referências

- `.github/workflows/`, `.github/dependabot.yml`, `docs/guides/governanca-github.md`.
