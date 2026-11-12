# Governança no GitHub

Configurações que o responsável pelo repositório precisa aplicar no GitHub. Elas não ficam em arquivos e não puderam ser aplicadas pela entrega de 2026-11-12 (sem acesso ao remoto). Decisões: [ADR-0014](../adr/0014-ci-e-controles-do-github.md) e [ADR-0018](../adr/0018-convencoes-de-commit-branch-e-versao.md).

## 1. Proteção de `main`

Em **Settings → Rules → Rulesets → New branch ruleset**, alvo `main`:

- Restrict deletions.
- Require linear history.
- Require a pull request before merging:
  - required approvals: **0** enquanto houver um único mantenedor; **1** quando houver o segundo;
  - dismiss stale approvals; require conversation resolution.
- Require status checks to pass, com a branch atualizada: `quality`, `tests (ubuntu-latest, 3.13)`, `tests (ubuntu-latest, 3.14)`, `tests (ubuntu-latest, 3.15)`, `tests (windows-latest, 3.13)`, `tests (windows-latest, 3.14)`, `tests (windows-latest, 3.15)`, `build` e `e2e (ubuntu-latest)`, `e2e (windows-latest)`. Os nomes aparecem depois da primeira execução da CI.
- Block force pushes.

Em **Settings → General → Pull Requests**: permitir apenas **squash merging**, com a mensagem padrão "Pull request title and description"; ativar a remoção automática de branches.

## 2. Segurança

Em **Settings → Code security**:

- Dependency graph e Dependabot alerts: ligados.
- Dependabot security updates: ligados.
- Secret scanning e push protection: ligados, se o plano permitir.
- Code scanning: **CodeQL, configuração padrão** (default setup), se o plano permitir.
- Private vulnerability reporting: ligado. É o canal citado em `SECURITY.md`.

Em repositório privado, secret scanning, push protection, code scanning e dependency review exigem GitHub Secret Protection e GitHub Code Security (planos Team e Enterprise). Em repositório público, são gratuitos. Sem eles, a análise estática de segurança continua na CI pelas regras `S` do Ruff.

## 3. Actions

Em **Settings → Actions → General**:

- Workflow permissions: **Read repository contents** (os workflows pedem permissões extras explicitamente);
- não permitir que o GitHub Actions crie ou aprove pull requests.

## 4. Branches antigas

Depois de reconciliar o histórico ([guia](recuperacao-do-historico.md)), remover do remoto `feature`, `feature-core` e `teste`, e triar os PRs abertos pelo Dependabot antes de 2026-11 (as dependências que eles atualizavam deixaram de existir).

## 5. Rótulos e formulários

- `.github/labels.yml` documenta os rótulos; crie-os pela interface ou com `gh label create`.
- Formulários de issue (bug, funcionalidade, RFC e ADR) e o template de PR ficam em `.github/`.
