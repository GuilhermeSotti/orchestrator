# Recuperação do histórico Git (2026-11-12)

## O que aconteceu

Em 2026-11-11 a pasta local tinha um `.git` incompleto: sem `refs`, com um único objeto e com 21 arquivos alterados que nunca tinham sido commitados ([auditoria](../audit/INITIAL_AUDIT.md)). Em 2026-11-12, `git init` tornou a pasta reconhecível de novo, mas sem commits nem objetos. O remoto `SicoloS-Guilherme-Machado/orchestrator` não estava acessível.

## O que foi feito

1. Um novo histórico foi criado a partir do estado da pasta. O commit-raiz guarda tudo o que existia, inclusive o trabalho nunca commitado, e recebeu a tag `archive/scaffold-2026-07`. Exceções: o e-mail pessoal do autor em `pyproject.toml` foi omitido, e três cópias duplicadas (`*-1.md`) não entraram.
2. Para 51 arquivos, o conteúdo é idêntico aos blobs do último commit conhecido (`6232d68`); o Git reconhece esses blobs como iguais quando o histórico remoto for buscado.
3. Os commits seguintes registram as decisões, a reestruturação e a implementação, um por entrega. Não houve Pull Requests: o remoto estava inacessível. Cada commit traz na mensagem o que um PR traria (objetivo, motivação, testes e impacto). As tags `orchestrator-core/v0.1.0`, `orchestrator-sql/v0.1.0` e `orchestrator-sqlite/v0.1.0` marcam o último commit.
4. A entrega não podia gravar dentro de `.git` nem de `.github`. Por isso o histórico novo chegou num bundle, `orchestrator-2026-11-12.bundle`, na raiz da pasta, e é importado com os comandos da seção seguinte. A importação não apaga nada: a configuração (inclusive o remoto `origin`) e os reflogs antigos continuam como estão, e as cópias do `HEAD` e do índice anteriores ficam em `.git/recovery-2026-11-12/`, junto com o bundle.

O histórico local **não tem ancestral comum** com o histórico remoto.

## Importar o histórico (uma vez)

Os arquivos da pasta, exceto os de `.github`, já estão na versão do último commit. Os comandos abaixo trazem o histórico do bundle, apontam o `HEAD` para `main`, trocam o índice e atualizam `.github`:

```powershell
cd C:\Users\Particular\Projetos\orchestrator
git bundle verify .\orchestrator-2026-11-12.bundle
New-Item -ItemType Directory -Force .git\recovery-2026-11-12 | Out-Null
Copy-Item .git\HEAD .git\recovery-2026-11-12\HEAD.antes
Copy-Item .git\index .git\recovery-2026-11-12\index.antes
git fetch .\orchestrator-2026-11-12.bundle "refs/heads/main:refs/heads/main" "refs/tags/*:refs/tags/*"
git symbolic-ref -m "recuperação: histórico local recriado em 2026-11-12" HEAD refs/heads/main
git read-tree refs/heads/main
git restore .github
Move-Item .\orchestrator-2026-11-12.bundle .git\recovery-2026-11-12\
git status
```

`git read-tree` substitui o índice antigo, que apontava para objetos inexistentes, pelo de `main`, sem tocar na pasta (`git reset` não serve aqui, porque tenta ler esses objetos). `git restore .github` grava os arquivos de `.github` na versão de `main`; as versões antigas estão no commit-raiz. Depois disso, `git status` deve listar apenas arquivos não rastreados (`??`), que a próxima seção remove, e `git log --oneline --decorate` deve mostrar os 11 commits e as quatro tags.

O bundle continua em `.git/recovery-2026-11-12/` como cópia independente do histórico: `git clone .git/recovery-2026-11-12/orchestrator-2026-11-12.bundle <pasta>` o restaura em outro lugar.

### Avisos esperados do Git

- `git status` informa que o upstream de `main` não existe: `origin/main` ainda não foi buscado. O aviso some depois do primeiro `git fetch` bem-sucedido.
- `git fsck` aponta `invalid reflog entry` nas entradas antigas dos reflogs: elas se referem a commits que só existem no remoto. O próximo `git gc` as expira (têm mais de 90 dias), e o `git fsck` passa a terminar sem erros.

## Limpeza da pasta depois da recuperação

**Só depois de importar o histórico.** Antes da importação o Git não conhece os arquivos novos, e `git clean` apagaria a maior parte do projeto e o próprio bundle.

Arquivos que saíram da árvore (o scaffold antigo, pastas sem conteúdo, duplicatas) continuam no disco, porque a entrega não podia apagar arquivos. Todos estão preservados no commit-raiz e na tag `archive/scaffold-2026-07`. Para removê-los:

```powershell
cd C:\Users\Particular\Projetos\orchestrator
git rev-parse --verify refs/heads/main   # precisa mostrar um hash; se der erro, importe o histórico antes
git status --short          # os arquivos que sobraram aparecem com ??
git clean -nd               # mostra o que seria removido, sem remover
git clean -fd               # remove; arquivos ignorados (.venv, caches) ficam
Remove-Item -Recurse -Force src, tests, packages\orchestrator_sql -ErrorAction SilentlyContinue
```

A última linha remove o que o `git clean` preserva por estar ignorado nas pastas do scaffold (`egg-info` e caches); essas pastas não fazem parte da árvore nova.

O `.venv` atual usa Python 3.11 e foi criado em outra máquina; o projeto exige Python 3.13 ou superior. Confira as versões instaladas com `py --list`, instale o 3.13 se faltar e recrie o ambiente:

```powershell
Remove-Item -Recurse -Force .venv
py -3.13 -m venv .venv
.venv\Scripts\python -m pip install -r requirements\dev.txt
.venv\Scripts\python -m pip install -e packages\orchestrator-core -e packages\orchestrator-sql -e packages\orchestrator-sqlite -e examples\hello-automation -e examples\sales-report
.venv\Scripts\python -m pytest
.venv\Scripts\python -m tools.e2e        # wheels num ambiente limpo e os dois exemplos
```

## Reconciliação com o remoto

Quando o acesso ao remoto voltar (com a conta que tem permissão):

```powershell
git fetch origin
git log --oneline --graph origin/main -15
git log --oneline 6232d689c0f89f2cea7f575eb946415d254c34b1..origin/main   # o que entrou no remoto depois de 2026-07-06
```

**Caminho recomendado: unir os históricos preservando os dois.**

```powershell
git switch -c chore/reconciliar-historico main
git merge --allow-unrelated-histories -s ours origin/main -m "chore: reconciliar o histórico local de 2026-11-12 com origin/main"
git push -u origin chore/reconciliar-historico
```

`-s ours` mantém exatamente a árvore local e registra `origin/main` como segundo pai, sem perder nenhum dos dois históricos. Antes, confira o resultado do segundo `git log` acima: mudanças que entraram no remoto depois de 2026-07-06 e não existem localmente precisam ser trazidas à mão. Abra o PR de `chore/reconciliar-historico` para `main` e use **merge commit** (não squash) nesta única vez, para preservar os dois históricos.

**Alternativa: reaplicar os commits sobre o remoto** (`git rebase --onto origin/main archive/scaffold-2026-07 main`). Mantém histórico linear, mas os primeiros commits vão conflitar com as versões remotas dos documentos.

Depois de reconciliar, envie as tags (`git push origin --tags`) e siga o [guia de governança](governanca-github.md).

## Autoria dos commits

Os commits foram criados pelo assistente de IA, com a identidade `Claude Opus 5.5 <noreply@anthropic.com>`. Se preferir a sua identidade, faça isto **antes** do primeiro envio ao remoto:

```powershell
git rebase -r --root --exec "git commit --amend --no-edit --reset-author"
```

O comando reescreve os commits e muda os seus identificadores; as tags precisariam ser recriadas.
