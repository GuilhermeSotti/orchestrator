# Auditoria técnica inicial — Orchestrator

| Campo | Valor |
|---|---|
| Data | 2026-11-11 |
| Objeto | Pasta local `C:\Users\Particular\Projetos\orchestrator` (remoto configurado: `https://github.com/SicoloS-Guilherme-Machado/orchestrator.git`) |
| Tipo | Diagnóstico da primeira execução (Fases A, B e C do plano de auditoria) |
| Situação | **Parcial** — o código-fonte não está disponível na pasta auditada e o remoto não é acessível nesta sessão |
| Atualização | O código foi adicionado à pasta depois deste relatório e auditado em `docs/audit/CODE_AUDIT.md`. A seção 13 indica o que muda na leitura deste documento |
| Documentos relacionados | `docs/audit/CODE_AUDIT.md`, `docs/IMPLEMENTATION_ROADMAP.md`, `docs/OPEN_DECISIONS.md` |

---

## 1. Resumo executivo

1. **A pasta local não é um repositório Git funcional e está incompleta (P0).** `.git/refs` não existe, `.git/objects` contém um único objeto e 72 dos 82 arquivos rastreados não estão no disco. `git status` responde `fatal: not a git repository`.
2. **O projeto não está apenas em "Planning".** O index do Git comprova que o commit `6232d68` (2026-07-06) continha um scaffold de `orchestrator_core` (38 arquivos Python, 23,6 KB), um pacote `orchestrator_sql` (11 arquivos, 25,8 KB), testes, CI, templates do GitHub e exemplos. Esse commit foi enviado a `origin/feature`. README, CHANGELOG e os documentos de contexto ainda descrevem o projeto como somente documental.
3. **Esse código não pôde ser auditado.** Só restam nomes, tamanhos e hashes. Toda afirmação sobre o conteúdo do Core está marcada como *provável* ou *não verificável*.
4. **O que é verificável já mostra divergências com a arquitetura documentada (P1):** implementação dentro do repositório de governança (monorepo de fato, sem ADR), `SQLAlchemy` declarada como "Core dependency", 5 estágios no scaffold contra 8 no lifecycle documentado, e `requires-python >=3.11` contra a stack-alvo 3.13+.
5. **O `pyproject.toml` local tinha sintaxe TOML inválida** em uma alteração não versionada; build, Pytest e Ruff falhavam antes de começar. Corrigido nesta sessão (uma linha).
6. **Nenhum segredo foi encontrado** nos arquivos presentes nem em `.git/config`.
7. **Controles do GitHub, CI, PRs e o estado de `main` não são verificáveis** sem acesso ao remoto. Há evidência indireta de que o Dependabot operava em julho e agosto de 2026.

**Recomendação imediata:** recuperar um clone íntegro (seção 3.6) antes de qualquer outra entrega, e então executar a auditoria complementar do código (Fase 0 do roadmap).

---

## 2. Escopo, método e limites

### 2.1 O que foi inspecionado

- Os 10 arquivos presentes na raiz da pasta, lidos integralmente.
- Os metadados remanescentes em `.git`: `HEAD`, `config`, `index`, `ORIG_HEAD`, `COMMIT_EDITMSG`, `FETCH_HEAD`, `info/exclude`, `gk/config`, reflogs em `logs/` e o único objeto existente.
- Os 8 documentos de contexto do Project (briefing, status, decisões em aberto, roadmap proposto, `CLAUDE.md`, prompt inicial, índice e README do kit).
- O repositório público `GuilhermeSotti/ai-harness` (somente README, `docs/` e listagem de arquivos), para determinar se o harness é utilizável.

### 2.2 Como foi inspecionado

- A sessão não dispõe de shell no computador do usuário. Os arquivos foram copiados para um ambiente de análise isolado (Linux, Python 3.13.18, Git 2.43.0, Ruff 0.16.9, MyPy 2.3.1, Pytest 9.1.1, setuptools 84.0.0, pip 26.2.1) e todas as verificações rodaram sobre essa cópia.
- **Nenhum comando Git foi executado na pasta do usuário.** Nenhum reparo foi tentado, para não destruir evidências nem alterar o que resta do histórico local.
- Nada foi enviado ao remoto. Nenhum commit, push, release ou publicação foi feito.

### 2.3 Limites desta auditoria

| Limite | Consequência |
|---|---|
| Código-fonte ausente da pasta | Core, pacote SQL, testes, CI e templates não foram lidos nem executados |
| Remoto fora do alcance da credencial da sessão (exige autenticação) | Estado de `main`, PRs, execuções de CI e configurações do GitHub não verificados |
| Sem shell no computador do usuário | Versões de Python e ferramentas instaladas na máquina não verificadas |
| `ai-harness` não conectado à sessão | Nenhuma revisão independente por agentes foi realizada (seção 10) |

### 2.4 Convenções de classificação

- **Achados:** *Confirmado* (evidência direta nesta sessão), *Provável* (evidência indireta forte: nomes, tamanhos e hashes no index, reflogs), *Proposta* (melhoria sugerida), *Não verificável* (depende de acesso indisponível).
- **Status por área:** *Implementado e validado*, *Parcial*, *Documentado/proposto*, *Ausente*, *Não verificável*.
- **Prioridade:** P0 crítico, P1 alto, P2 médio, P3 baixo.

---

## 3. Estado do repositório local

### 3.1 Evidências

| Evidência | Resultado |
|---|---|
| Listagem de `.git` | Presentes: `COMMIT_EDITMSG`, `config`, `description`, `FETCH_HEAD` (0 bytes), `HEAD`, `index`, `ORIG_HEAD`, `gk/`, `hooks/` (apenas `*.sample`), `info/`, `logs/`, `objects/` |
| `.git/refs` | **Não existe** |
| `.git/objects` | **1 objeto** (`01/72051186…`, blob de 87 bytes); `objects/pack` não existe |
| `.git/packed-refs` | Não existe |
| `git status` sobre cópia fiel de `.git` | `fatal: not a git repository (or any of the parent directories): .git` |
| `HEAD` | `ref: refs/heads/feature` |
| Index | 82 entradas, checksum SHA-1 íntegro |
| Diretórios `src`, `tests`, `packages`, `.github`, `docs` | **Não existem** no disco |
| Arquivos na raiz | 10 arquivos (seção 4.1) |

### 3.2 O que o index revela

- O index lista **82 arquivos rastreados** (85.371 bytes). Apenas 10 estão no disco; **72 arquivos (67.426 bytes) estão ausentes**.
- A extensão `TREE` do index (cache-tree) está **inteiramente válida**: raiz `b1e2d4211fa299bf9cbef24c748193b133c45039`, 82 entradas. Isso significa que, na última escrita do index (2026-07-06 18:02), o index correspondia exatamente a uma árvore já gravada. Como o último movimento de `HEAD` no reflog é o `reset` para `6232d68`, o mais provável é que seja a árvore desse commit, ou seja, que **não houvesse alteração em stage**.
- Dos 10 arquivos presentes, **9 são idênticos** ao conteúdo registrado no index (hash de blob igual após normalizar CRLF→LF). **`pyproject.toml` difere**: há uma alteração local não versionada, feita em 2026-07-21. O conteúdo versionado não pôde ser recuperado (o objeto não existe localmente).

### 3.3 Linha do tempo reconstruída pelos reflogs

Horários em America/Sao_Paulo.

| Data e hora | Evento |
|---|---|
| 2026-06-30 13:28 | `git init` e primeiro `git add` |
| 2026-06-30 13:30 | Commit inicial `ffd8852` em `main` |
| 2026-06-30 14:25 e 15:07 | Commits `e6d4845` e `b9eac71` em `main`, com a mesma mensagem do inicial |
| 2026-06-30 15:10–15:12 | Branch `teste` criada e enviada (`origin/teste` = `b9eac71`) |
| 2026-06-30 15:15 | Commit `4c4ff0c` ("modified: ROADMAP.md") em HEAD destacado; `main` recriada a partir dele |
| 2026-06-30 15:16 | Push: `origin/main` = `4c4ff0c` |
| 2026-07-01 10:17 e 12:06 | Fetch de `origin/feature-core` e `origin/feature`, ambas em `4c4ff0c` |
| 2026-07-06 15:37 | Commit `6232d68` em `feature-core`: "feat: initialize orchestrator-core project structure with core components" |
| 2026-07-06 16:03 | `feature` movida por `reset` para `6232d68` |
| 2026-07-06 16:04 | Push: `origin/feature` = `6232d68` |
| 2026-07-06 16:26 | Fetch: `origin/main` avança de `4c4ff0c` para `d56bcce` |
| 2026-07-06 18:02 | Última escrita do index |
| 2026-07-20 15:05 | Fetch traz branches do Dependabot: pip (`pytest`, `pytest-cov`, `setuptools`, `sqlalchemy`) e GitHub Actions (`actions/checkout`, `actions/setup-python`) |
| 2026-07-21 11:51 | `pyproject.toml` modificado localmente, sem commit |
| 2026-08-26 13:30 | Fetch traz novas branches do Dependabot (`setuptools`, `sqlalchemy`) |
| 2026-11-01 21:07 | `FETCH_HEAD` regravado com 0 bytes (compatível com um fetch sem sucesso); metadado do GitLens/GitKraken atualizado |
| 2026-11-02 13:14 | `GOVERNANCE.md` regravado sem mudança de conteúdo |
| Depois de 2026-11-02 | A pasta passa ao estado incompleto atual (inferido pelas datas de modificação; data exata não determinável) |

Observações:

- `main` local ficou em `4c4ff0c`; `origin/main` foi visto pela última vez em `d56bcce`. O avanço 22 minutos após o push de `feature` é compatível com o merge de um Pull Request, mas isso não é verificável.
- `origin/feature-core` permaneceu em `4c4ff0c` e `origin/teste` em `b9eac71`: são branches residuais no remoto, se ainda existirem.

### 3.4 Hipótese de causa (não confirmada)

O padrão do que restou é compatível com uma **cópia ou movimentação de pasta interrompida**, feita por uma ferramenta que processa primeiro os arquivos de cada diretório e depois os subdiretórios em ordem alfabética:

- todos os arquivos da raiz e todos os arquivos diretamente em `.git` estão presentes;
- em `.git`, os subdiretórios `gk`, `hooks`, `info` e `logs` estão completos, `objects` contém apenas a primeira entrada (`01/…`) e `refs`, que vem depois, não existe;
- todos os subdiretórios da raiz que viriam depois de `.git` (`.github`, `assets`, `examples`, `packages`, `src`, `templates`, `tests`) estão ausentes;
- o reflog registra o hostname `DESKTOP-OOD6P4D`, diferente do computador atual (`desktop-64fafml`).

Outras causas (limpeza por ferramenta, exclusão manual, falha de sincronização) não podem ser descartadas com as evidências disponíveis.

### 3.5 O que provavelmente está preservado e o que está em risco

| Item | Situação |
|---|---|
| Commits até `6232d68` | Provavelmente preservados no remoto (`origin/feature` recebeu o push; `origin/main` avançou em seguida). Não verificável nesta sessão |
| Alterações em stage no momento da última escrita do index | Provavelmente não havia (cache-tree válida) |
| Alteração local de `pyproject.toml` (2026-07-21) | Presente no disco |
| Alterações não commitadas nos 72 arquivos ausentes, feitas depois de 2026-07-06 18:02 | **Indeterminado.** Se existiram, só estão na pasta de origem |
| Reflogs locais | Presentes; são o único registro local do histórico |

### 3.6 Procedimento de recuperação recomendado (não executado)

Ordem de preferência:

1. **Localizar a pasta de origem.** Se esta pasta foi copiada, movida, restaurada de backup ou sincronizada a partir de outro local (outro caminho, outro disco, a máquina `DESKTOP-OOD6P4D`), a origem contém o repositório completo, inclusive o que nunca foi enviado ao remoto. É a melhor fonte.
2. **Clonar novamente do GitHub**, com a conta que tem acesso ao remoto, em uma pasta nova.
3. Se nenhuma das duas existir, restam apenas os 10 arquivos desta pasta; o código precisará ser refeito conforme o roadmap.

Comandos sugeridos para a opção 2 (PowerShell):

```powershell
# 1) Cópia de segurança da pasta atual: preserva reflogs, o pyproject.toml alterado e docs/
robocopy C:\Users\Particular\Projetos\orchestrator C:\Users\Particular\Projetos\orchestrator.parcial-2026-11-11 /E /COPY:DAT /DCOPY:T /R:1 /W:1

# 2) Clone íntegro em pasta nova
git clone https://github.com/SicoloS-Guilherme-Machado/orchestrator.git C:\Users\Particular\Projetos\orchestrator-restaurado
cd C:\Users\Particular\Projetos\orchestrator-restaurado

# 3) Verificações de integridade e de correspondência com o index antigo
git fsck --full
git cat-file -t 6232d689c0f89f2cea7f575eb946415d254c34b1            # esperado: commit
git rev-parse "6232d689c0f89f2cea7f575eb946415d254c34b1^{tree}"     # esperado: b1e2d4211fa299bf9cbef24c748193b133c45039
git merge-base --is-ancestor 6232d689c0f89f2cea7f575eb946415d254c34b1 origin/main; $LASTEXITCODE   # 0 = já está em main
git log --oneline --graph --all -20

# 4) Comparar, sem sobrescrever, os arquivos alterados na pasta parcial
git diff --no-index -- pyproject.toml ..\orchestrator.parcial-2026-11-11\pyproject.toml
```

Cuidados:

- Não apagar a pasta atual antes de validar o clone.
- `main` remoto pode estar à frente do retrato local (o último fetch bem-sucedido é de 2026-08-26). Os arquivos alterados nesta sessão (seção 11) devem ser **comparados**, não copiados por cima.
- As alterações desta sessão devem entrar por branch `fix/*` e Pull Request, conforme `GOVERNANCE.md`.

---

## 4. Inventário

### 4.1 Arquivos presentes no disco

| Arquivo | Bytes | Em relação ao index | Observação |
|---|---:|---|---|
| `.gitignore` | 219 | Idêntico | Padrão `mypy_cache/` incorreto; faltavam artefatos de build (corrigido, seção 11) |
| `ARCHITECTURE.md` | 5.074 | Idêntico | Em inglês; alterado ou adicionado em `6232d68` |
| `CHANGELOG.md` | 151 | Idêntico | Somente `[Unreleased]` com 3 itens |
| `CONTRIBUTING.md` | 421 | Idêntico | Em português; mínimo |
| `GOVERNANCE.md` | 3.450 | Idêntico | Em inglês; alterado ou adicionado em `6232d68` |
| `LICENSE` | 1.095 | Idêntico | Texto MIT padrão, copyright 2026 em nome de pessoa física |
| `README.md` | 1.864 | Idêntico | Em português; status "Planning" |
| `SECURITY.md` | 4.990 | Idêntico | Em inglês; alterado ou adicionado em `6232d68` |
| `pyproject.toml` | 625 | **Difere** | Alteração local não versionada, com erro de sintaxe (corrigido, seção 11) |
| `requirements.txt` | 98 | Idêntico | `SQLAlchemy>=2.0`, `pytest>=7.0`, `pytest-cov>=4.0` |

Todos os arquivos estão em UTF-8 sem BOM e com fim de linha CRLF. Não há `.gitattributes`.

### 4.2 Arquivos rastreados no index e ausentes do disco

| Grupo | Arquivos | Bytes | Conteúdo (pelos nomes) |
|---|---:|---:|---|
| `src/orchestrator_core/` | 38 | 23.635 | `__init__`, `bootstrap`, `config_loader`, `context`, `events`, `execution_engine`, `logging_service`, `main` (CLI), `pipeline`, `registry`, `runner/`, `runner_port`, `spec`, `specification`, `utils`, `adapters/in_memory`, `ports/` (13 arquivos), `stage/` (7 arquivos) |
| `src/orchestrator_core.egg-info/` | 5 | 3.537 | Artefatos de build versionados |
| `tests/` | 2 | 3.449 | `test_architecture_modules.py`, `test_core_runtime.py` |
| `packages/orchestrator_sql/` | 11 | 25.826 | `pyproject.toml`, `README.md`, `sql_provider.py` (11,1 KB), `mappers/table_mapper.py` (6,9 KB), `schema_manager.py`, `query_executor.py`, 3 arquivos de teste |
| `packages/README.md` | 1 | 99 | Marcador de diretório |
| `.github/` | 10 | 9.156 | `CODEOWNERS`, `PULL_REQUEST_TEMPLATE.md`, `dependabot.yml`, `labels.yml`, `workflows/ci.yml` (456 bytes), 5 templates de issue (`adr_proposal`, `bug_report`, `config`, `feature_request`, `rfc`) |
| `examples/` | 3 | 1.532 | `README.md`, `basic-spec.json`, `sql-spec.json` |
| `assets/`, `templates/` | 2 | 192 | Marcadores `README.md` |
| **Total** | **72** | **67.426** | |

A lista completa está no Apêndice A.

### 4.3 Itens citados na documentação e ausentes do disco e do index

| Item | Onde é citado | Evidência adicional |
|---|---|---|
| `ROADMAP.md` | Estrutura do README; CHANGELOG ("Roadmap inicial") | O reflog registra o commit "modified: ROADMAP.md" (`4c4ff0c`): o arquivo existiu e deixou de ser rastreado até `6232d68` |
| `docs/` | Estrutura do README; `GOVERNANCE.md` (`docs/adr/`) | O único objeto remanescente é um blob com o texto de um README de diretório de documentação, compatível com `docs/README.md` do commit inicial |
| `ADR/` na raiz | Estrutura do README | Conflita com `docs/adr/` de `GOVERNANCE.md` |
| `scripts/`, `config/` | Estrutura do README | — |
| `CODE_OF_CONDUCT.md` | Estrutura do README | — |

### 4.4 Instruções, agentes e ferramentas no repositório

| Item | Situação |
|---|---|
| `CLAUDE.md`, `AGENTS.md`, `.claude/` | Ausentes do disco e do index |
| Skills, workflows de agentes, servidores MCP configurados no repositório | Ausentes |
| Hooks do Git | Apenas arquivos `*.sample`; nenhum hook ativo |
| Lockfile (`uv.lock`, `poetry.lock`, `requirements*.txt` com hashes, `pylock.toml`) | Ausente |
| Configuração de Ruff e MyPy | Ausente no `pyproject.toml` local |
| ADRs e RFCs | Nenhum |

---

## 5. Matriz de status por área

"Index" significa evidência por nome, tamanho e hash do arquivo na árvore `b1e2d42`; o conteúdo não foi lido.

| Área | Status | Evidência |
|---|---|---|
| Visão, arquitetura e governança documentadas | Documentado | 6 documentos presentes e idênticos ao index |
| Templates e governança GitHub (issues, PR, CODEOWNERS, labels) | Parcial, não validado | Index: `.github/` com 10 arquivos; ausentes do disco; aplicação no GitHub não verificável |
| CI | Parcial, não validado | Index: `workflows/ci.yml` (456 bytes); execuções não verificáveis |
| Core e Runtime (`orchestrator_core`) | Parcial, não validado | Index: 38 arquivos; ausentes do disco |
| Execution Pipeline e estágios | Parcial, não validado | Index: `pipeline.py`, `execution_engine.py`, `stage/` com 5 estágios concretos |
| Execution Context | Parcial, não validado | Index: `context.py` (1.143 bytes) |
| Configuration | Parcial, não validado | Index: `config_loader.py`, `ports/configuration.py` |
| Dependency Injection | Não verificável | Index: `bootstrap.py` (557 bytes) sugere raiz de composição |
| Event Bus | Parcial, não validado | Index: `events.py`, `ports/event.py` |
| Logging | Parcial, não validado | Index: `logging_service.py`, `ports/logging_port.py`, `stage/logging_stage.py` |
| Metrics | Parcial, não validado | Index: `ports/metrics.py` e `ports/metrics_port.py` (duplicidade) |
| Retry | Ausente na árvore | Nenhum arquivo com esse nome; pode existir dentro de outro módulo |
| Capability Registry | Parcial, não validado | Index: `registry.py` (909 bytes) |
| Capabilities | Parcial, não validado | Index: `packages/orchestrator_sql/` |
| Providers | Parcial, não validado | Index: `adapters/in_memory.py`, `sql_provider.py` |
| Public API | Não definida | Index: `__init__.py` (665 bytes) e CLI `orchestrator_core.main:cli`; sem documentação de API |
| Testes | Parcial, não executados | Index: 2 arquivos no Core e 3 no pacote SQL |
| Empacotamento | Parcial e quebrado localmente | `pyproject.toml` era inválido (corrigido, seção 11); `src/` ausente (seção 6) |
| Exemplo de projeto consumidor | Parcial, não validado | Index: 2 specs JSON em `examples/`; nenhum projeto consumidor Python |
| ADRs e RFCs | Ausente | `docs/adr/` não existe; nenhum registro |
| Controles de segurança do GitHub | Não verificável | Evidência indireta apenas para Dependabot |
| Releases e publicação de pacotes | Não verificável | `version = "0.1.0"` declarada; nenhuma evidência de publicação |

---

## 6. Verificações executadas

| # | Verificação | Resultado | Classe |
|---:|---|---|---|
| 1 | `git status` sobre cópia fiel de `.git` | `fatal: not a git repository` | Reprovado |
| 2 | Leitura do index (`git ls-files --stage` e `--debug`; leitura da extensão `TREE`; checksum) | 82 entradas; cache-tree válida, raiz `b1e2d42…`; checksum confere | Aprovado |
| 3 | Comparação de conteúdo entre arquivos do disco e index (hash de blob, CRLF→LF) | 9 idênticos; `pyproject.toml` difere | Aprovado com ressalva |
| 4 | Validação TOML de `pyproject.toml` (`tomllib`) | Inválido: `Expected '=' after a key in a key/value pair (at line 11, column 61)` | Reprovado |
| 5 | `ruff check` e `ruff format --check` | Saída 2: falha ao ler `pyproject.toml` | Reprovado |
| 6 | `mypy` | Saída 2: `There are no .py[i] files` | Não aplicável |
| 7 | `pytest` | Saída 4: erro de configuração (TOML inválido) | Reprovado |
| 8 | Build: `pip wheel --no-deps --no-build-isolation` | Saída 2: `TOMLDecodeError` | Reprovado |
| 9 | Itens 5 a 8 repetidos sobre cópia com a sintaxe corrigida | Ruff: saída 0 (só `pyproject.toml` analisado; não há arquivos Python). Pytest: saída 5, nenhum teste coletado. Build: saída 1, `error in 'egg_base' option: 'src' does not exist or is not a directory` | Reprovado (build) |
| 10 | Aviso de depreciação no build | setuptools 84.0.0: `project.license` como tabela TOML está depreciado; prazo informado pelo aviso: 2027-02-18 | Confirmado |
| 11 | Varredura de segredos nos 10 arquivos e nos metadados textuais de `.git` (tokens do GitHub, chaves AWS, chaves privadas, URLs com credenciais, atribuições de senha ou token) | 0 ocorrências | Aprovado |
| 12 | Codificação e fim de linha | UTF-8 sem BOM; CRLF; 3 arquivos sem quebra de linha final | Aprovado |
| 13 | Conflito de nomes `feature` × `feature/*` em repositório descartável | `fatal: cannot lock ref 'refs/heads/feature/…': 'refs/heads/feature' exists` | Confirmado |
| 14 | Acesso ao remoto (leitura sem credenciais; tentativa de anexar o repositório à sessão) | Autenticação exigida; credencial da sessão sem acesso. Compatível com repositório privado, renomeado ou removido | Bloqueado |
| 15 | Testes do Core e do pacote SQL, cobertura, CI | — | Não executado (código ausente) |
| 16 | Controles e configurações do GitHub | — | Bloqueado (sem acesso) |
| 17 | Versões de Python e ferramentas no computador do usuário | — | Não executado (sem shell no computador) |

---

## 7. Achados priorizados

### 7.1 P0 — crítico

| ID | Achado | Classe | Evidência | Impacto | Recomendação |
|---|---|---|---|---|---|
| REP-01 | Clone local sem `refs`, com 1 objeto e 72 de 82 arquivos rastreados ausentes | Confirmado | Seção 3.1 e 3.2 | Sem versionamento local; código inacessível; risco de perda do que não foi enviado ao remoto | Seção 3.6. Causa-raiz não confirmada (seção 3.4) |

### 7.2 P1 — alto

| ID | Achado | Classe | Evidência | Impacto | Recomendação |
|---|---|---|---|---|---|
| REP-02 | Remoto inacessível nesta sessão | Não verificável | Verificação 14 | Estado de `main`, PRs, CI e controles do GitHub desconhecidos | Conceder acesso ao remoto ou trabalhar a partir de um clone íntegro |
| REP-03 | `pyproject.toml` com alteração não versionada e TOML inválido (`mail:` no lugar de `email =`) | Confirmado | Verificações 4, 5, 7 e 8 | Build, Pytest e Ruff falham antes de iniciar | Corrigido (seção 11) |
| PKG-01 | Build impossível mesmo com a sintaxe corrigida: `src/` não existe | Confirmado | Verificação 9 | Pacote não instalável a partir desta pasta | Consequência de REP-01 |
| ARQ-01 | Repositório de governança contém implementação: `pyproject.toml` com `name = "orchestrator-core"`, `src/orchestrator_core/` e `packages/orchestrator_sql/` | Confirmado (estrutura) | Index; `pyproject.toml` | Monorepo de fato, em conflito com a estratégia multirrepositório de README, ARCHITECTURE e GOVERNANCE, sem ADR | Decisão D-01 |
| ARQ-02 | `requirements.txt` declara `SQLAlchemy>=2.0` como "Core dependencies"; `pyproject.toml` declara `dependencies = []` | Confirmado (declaração) | Arquivos presentes | Contraria "The Core must never depend on infrastructure"; duas fontes de verdade divergentes | Remover do Core; decisões D-01, D-04 e D-18. Se o código do Core importa SQLAlchemy: não verificável |
| ARQ-03 | Scaffold com 5 estágios (`initialize`, `execute`, `finalize`, `logging`, `shutdown`) contra 8 no lifecycle documentado | Provável | Index: `stage/` | ARCHITECTURE afirma no presente que o lifecycle está implementado como pipeline | Decisão D-06; auditoria complementar |
| ARQ-04 | Core com 13 arquivos de ports (média de 311 bytes), incluindo contratos específicos de capability (`cache`, `queue`, `notification`, `storage`, `secrets`, `artifact`, `infrastructure`) e duplicidades (`metrics` × `metrics_port`; `spec` × `specification`; `runner/` × `runner_port`) | Provável | Index | Tendência a Core largo e raso; abstrações sem consumidor | Decisão D-03; auditoria complementar |
| ARQ-05 | Forma da Public API não definida; o scaffold aparenta ser orientado a specs JSON executadas por CLI | Provável | Index: `examples/*-spec.json`, `spec.py`, `main.py`; `[project.scripts]` | Risco de deslocar lógica do consumidor para specs e de antecipar um workflow engine | Decisão D-02 |

### 7.3 P2 — médio

| ID | Achado | Classe | Evidência | Recomendação |
|---|---|---|---|---|
| PKG-02 | `requires-python = ">=3.11"` contra a stack-alvo "Python 3.13+" | Confirmado | `pyproject.toml`; ARCHITECTURE | Decisão D-17 |
| PKG-03 | Ruff e MyPy sem configuração e sem declaração como dependência; Pydantic não declarado; sem lockfile; `requirements.txt` sem versões fixadas | Confirmado | Arquivos presentes | Decisão D-18; Fase 1 |
| PKG-04 | `license = { text = "MIT" }` depreciado no setuptools, com prazo 2027-02-18; `requires = ["setuptools>=68"]` sem limite superior | Confirmado | Verificação 10 | Migrar para expressão SPDX (`license = "MIT"`) com `setuptools>=77` |
| REP-04 | Artefatos de build versionados (`src/orchestrator_core.egg-info/`, 5 arquivos) | Confirmado (index) | Index | `git rm -r --cached` após recuperar; `.gitignore` corrigido (seção 11) |
| REP-05 | Histórico fora da política: 4 commits diretos em `main` em 2026-06-30; branches `feature`, `feature-core` e `teste` fora do padrão `feature/*` | Confirmado | Reflogs | Renomear ou remover branches; ativar proteção de `main` |
| REP-06 | A branch `feature` impede a criação de qualquer `feature/*` no mesmo repositório | Confirmado | Verificação 13 | Renomear `feature` (por exemplo `feature/core-scaffold`) ou removê-la após o merge, no local e no remoto |
| REP-07 | Branches do Dependabot vistas em dois fetches com cerca de cinco semanas de intervalo, inclusive para `sqlalchemy`; indício de PRs acumulados | Provável | Reflogs | Triar os PRs abertos; rever o escopo do Dependabot após a decisão D-01 |
| GOV-01 | Funcionalidade grande (Core, CLI, pacote SQL) entrou em commit único, sem RFC ou ADR localizável | Confirmado pelo index | Index; `COMMIT_EDITMSG` | Registrar retroativamente as decisões (D-00, D-01, D-02) |
| GOV-02 | Identidades divergentes: remoto na conta `SicoloS-Guilherme-Machado`, commits com e-mail corporativo, LICENSE com copyright de pessoa física, autor do pacote com e-mail pessoal | Confirmado | `.git/config`, reflogs, `LICENSE`, `pyproject.toml` | Decisão D-23. Não é parecer jurídico |
| GOV-03 | Nome do repositório remoto (`orchestrator`) difere do nome usado na documentação (`orchestrator-platform`) | Confirmado | `.git/config`; README | Decisão D-01 |
| DOC-01 | README: "Status: Planning" e "Estrutura inicial" não correspondem à árvore rastreada (cita 6 itens inexistentes e omite `src/`, `tests/`, `pyproject.toml`, `requirements.txt`) | Confirmado | README; index | Reescrever após recuperar o repositório e decidir D-01 |
| DOC-02 | CHANGELOG não registra o que o commit `6232d68` adicionou e cita um roadmap que deixou de ser rastreado | Confirmado | CHANGELOG; index | Adotar formato com seções por tipo e por versão; registrar retroativamente |
| DOC-03 | `docs/adr/` exigido por GOVERNANCE não existe; README cita `ADR/` na raiz | Confirmado | Seção 4.3 | Criar `docs/adr/` com modelo e índice (Fase 1) |
| DOC-04 | SECURITY.md não informa canal de reporte privado e descreve no presente validações de CI não evidenciadas | Confirmado (documento); Provável (CI) | SECURITY.md; `ci.yml` de 456 bytes | Indicar canal; alinhar o texto ao que estiver configurado |
| DOC-05 | ARCHITECTURE: o diagrama "Dependency Rule" coloca "Public API" como camada mais interna; "Providers must implement contracts defined by the Core" conflita com a camada de Capabilities | Confirmado (documento) | ARCHITECTURE.md | Decisão D-03 |
| DOC-06 | SECURITY: "The Core must never depend directly on third-party libraries" conflita com Pydantic na stack-alvo | Confirmado (documento) | SECURITY.md; ARCHITECTURE.md | Decisão D-04 |
| SEC-01 | Controles declarados obrigatórios (Secret Scanning, CodeQL, Dependency Review) podem não estar disponíveis para repositório privado, conforme o tipo de conta e o plano | Não verificável | Seção 9.2 | Decisão D-19 |
| SEC-02 | Pontos do código ausente que exigem revisão de segurança prioritária | Não verificável | Seção 8.4 | Auditoria complementar |

### 7.4 P3 — baixo

| ID | Achado | Classe | Recomendação |
|---|---|---|---|
| REP-08 | Mensagens de commit sem convenção: 3 commits com mensagem idêntica; "modified: ROADMAP.md" | Confirmado | Decisão D-24 |
| REP-09 | Sem `.gitattributes`; a normalização de fim de linha depende da configuração global de cada máquina | Confirmado | Adicionar `.gitattributes` (Fase 1) |
| GOV-04 | Os prefixos de branch de GOVERNANCE não cobrem mudanças só de documentação ou manutenção | Confirmado | Decisão D-24 |
| DOC-07 | Idioma misto sem política: README, CONTRIBUTING e CHANGELOG em português; ARCHITECTURE, GOVERNANCE e SECURITY em inglês | Confirmado | Decisão D-23 |
| DOC-08 | CONTRIBUTING não reflete as regras de GOVERNANCE (nomes de branch, conteúdo do PR, ADR/RFC, ferramentas) | Confirmado | Fase 1 |
| DOC-09 | Erro de digitação no README ("Estratégia de reposição") | Confirmado | Corrigido (seção 11) |
| DOC-10 | SECURITY traz tabela de versões suportadas com LTS sem que exista release | Confirmado | Ajustar na primeira release |
| PKG-05 | `readme = "README.md"` faria o pacote `orchestrator-core` publicar o README de governança; comando `orchestrator` é genérico | Confirmado | Resolver com D-01 e D-02 |

---

## 8. Avaliação arquitetural

### 8.1 O que pode ser afirmado

- **Direção das dependências.** No nível declarativo há uma violação: SQLAlchemy aparece como dependência do Core em `requirements.txt` (ARQ-02). No nível estrutural, uma capability SQL vive dentro do mesmo repositório do Core (ARQ-01). No nível de código, nada pode ser afirmado.
- **Tamanho do Core.** Os 38 arquivos somam 23,6 KB. A parte de ports tem 13 arquivos com média de 311 bytes: contratos numerosos e muito pequenos, vários deles específicos de capabilities que ainda não existem. Isso é o perfil de abstração antecipada que as próprias diretrizes do projeto pedem para evitar (ARQ-04).
- **Lifecycle.** A árvore tem 5 estágios concretos; os estágios Provision Dependencies, Prepare Environment e Prepare Execution não têm arquivo correspondente (ARQ-03).
- **Fronteira Capability e Provider.** O pacote `orchestrator_sql` contém `sql_provider.py`; contrato e implementação concreta parecem conviver no mesmo pacote, o que contraria o vocabulário do projeto. Provável, pelo nome dos arquivos.
- **Public API.** Não há documento nem evidência de uma superfície pública definida (ARQ-05).

### 8.2 Ambiguidades nos próprios documentos de arquitetura

- O diagrama "High Level Architecture" mostra fluxo de controle; o diagrama "Dependency Rule" mostra dependência. As setas têm significados diferentes e o segundo posiciona "Public API" como o elemento do qual o Core depende.
- "Providers must implement contracts defined by the Core" não diz onde vivem os contratos funcionais de cada capability.
- Falhas, cancelamento, timeout, retry, concorrência e cleanup do pipeline não estão especificados.
- "Provision Dependencies" e "Persist Logs" não têm semântica definida.

Todas estão registradas como decisões em `docs/OPEN_DECISIONS.md`.

### 8.3 Conformidade com os princípios, no que é verificável

| Princípio | Situação |
|---|---|
| Core independente de infraestrutura | Violado na declaração de dependências; código não verificável |
| Core pequeno | Em dúvida (ARQ-04) |
| Extensão sem alterar o Core | Não verificável; ports de capability dentro do Core indicam o contrário |
| Dependências explícitas | Não atendido: duas fontes divergentes, sem lockfile |
| Testabilidade | Não verificável |
| Estratégia multirrepositório | Não seguida na prática (ARQ-01) |
| Compatibilidade declarada | Divergente (PKG-02) |

### 8.4 Roteiro para a auditoria complementar do código

Quando o código estiver acessível, inspecionar primeiro:

1. Imports de `orchestrator_core`: algum módulo importa `sqlalchemy`, `orchestrator_sql` ou outra biblioteca de terceiros?
2. Estado global e singletons em `registry.py`, `bootstrap.py`, `logging_service.py` e `events.py`.
3. Garantias de finalização em `pipeline.py` e `execution_engine.py`: o que roda quando um estágio falha.
4. Carregamento de specs em `spec.py`, `config_loader.py` e `main.py`: import dinâmico, caminhos de arquivo, validação de entrada.
5. Construção de SQL em `query_executor.py`, `table_mapper.py` e `sql_provider.py`: parametrização e injeção.
6. `examples/sql-spec.json`: presença de connection string ou credenciais.
7. Sanitização em `logging_service.py`.
8. Cobertura real dos 5 arquivos de teste e resultado de Ruff, MyPy e Pytest.
9. Conteúdo de `.github/workflows/ci.yml`, `dependabot.yml` e `CODEOWNERS`.

---

## 9. Governança e segurança

### 9.1 Aderência do histórico à política documentada

| Regra de `GOVERNANCE.md` | Situação |
|---|---|
| Commits diretos em `main` proibidos | 4 commits diretos em 2026-06-30 (o inicial é inevitável) |
| Branches temporárias com prefixo | `feature`, `feature-core` e `teste` não seguem o padrão |
| Mudanças por Pull Request | Provável para `6232d68`; não verificável |
| ADR para mudança arquitetural significativa | Nenhum ADR |
| RFC antes de funcionalidade grande | Nenhum RFC |
| Changelog atualizado | Não reflete `6232d68` |
| CI aprovada | Não verificável |

### 9.2 Controles do GitHub

- **Não verificável:** proteção de `main` ou rulesets, checks obrigatórios, Secret Scanning, Push Protection, CodeQL, Dependency Review, releases assinadas, aplicação de `CODEOWNERS` e de `labels.yml`.
- **Evidência indireta:** branches `dependabot/pip/*` e `dependabot/github_actions/*` em fetches de 2026-07-20 e 2026-08-26 indicam Dependabot em operação naquele período.
- **Ponto de atenção:** segundo a documentação do GitHub, em repositórios privados o secret scanning e o push protection dependem do produto GitHub Secret Protection, e o code scanning e o dependency review dependem do GitHub Code Security, ambos contratáveis nos planos Team e Enterprise; em repositórios públicos esses recursos são gratuitos. O remoto não respondeu a leitura anônima, o que é compatível com repositório privado. Se o repositório pertence a uma conta de usuário ou a um plano sem esses produtos, parte dos controles que `GOVERNANCE.md` declara obrigatórios não pode ser habilitada. A verificação depende de acesso às configurações (decisão D-19).

### 9.3 Segurança dos arquivos presentes

- Nenhum segredo encontrado (verificação 11). `.git/config` não contém credenciais na URL do remoto.
- `.gitignore` não ignorava arquivos `.env` (corrigido).
- `pyproject.toml` contém o e-mail pessoal do autor e os reflogs contêm um e-mail corporativo. Não é exposição de segredo; é uma escolha a revisar em D-23.

---

## 10. Instruções do projeto e AI-Harness

### 10.1 Instruções

- **No repositório:** não há `CLAUDE.md`, `AGENTS.md` nem `.claude/`.
- **No Project:** existem `CLAUDE.md` e os documentos do kit. O `CLAUDE.md` remete a `original_docs/` e `docs/` do repositório, que não existem na pasta. A incorporação do kit ao repositório, prevista em `README_KIT.md`, não foi feita.
- **Conflito entre instruções:** o prompt inicial do kit proíbe qualquer alteração durante a auditoria; a solicitação desta sessão autoriza a correção de problemas claros. Prevaleceu a solicitação mais recente e mais específica, limitada a quatro correções mínimas (seção 11). Nenhuma funcionalidade foi implementada.
- **Trecho herdado de outro projeto:** a seção sobre `ai-harness` das instruções do Project diz que o harness "deve apoiar o desenvolvimento do ConsolidaHub" e lista competências de dados que não se aplicam ao Orchestrator. Recomenda-se ajustar o texto. As instruções não foram alteradas nesta sessão.

### 10.2 AI-Harness

| Verificação | Resultado |
|---|---|
| Localização | Pasta `ai-harness` ao lado desta, fora das pastas autorizadas para a sessão; repositório público `GuilhermeSotti/ai-harness` (commit `563868a`, 2026-10-27) |
| O que é, segundo a própria documentação | Pacote Python `ai-harness` 0.1.0 com CLI, Maestro, servidor MCP stdio (6 ferramentas) e dois agentes somente leitura: `analyst` e `reviewer` |
| Providers | Ollama local por padrão; Anthropic opcional com chave própria; provider simulado apenas para desenvolvimento |
| Estado declarado em 2026-10-27 | Servidor MCP registrado no Claude Code da máquina; **inferência real não verificada** (tentativas excederam o tempo limite); a lista de pastas legíveis incluía apenas o próprio `ai-harness` |
| Disponibilidade nesta sessão | **Indisponível.** Nenhum servidor MCP local anunciado; nenhuma ferramenta do harness na sessão; sem shell no computador para acionar a CLI |

Consequências:

- Esta auditoria foi feita sem o harness. **Nenhuma revisão independente por agentes foi realizada e nenhum resultado deste relatório vem do harness.**
- O código do harness não foi executado nem revisado; as informações acima vêm apenas do README e de `docs/AI_HARNESS_MCP.md`.
- Para usá-lo no Orchestrator seria necessário: incluir a pasta do Orchestrator em `AI_HARNESS_ALLOWED_ROOTS`; ter um provider que conclua a inferência; e trabalhar em um cliente no qual o servidor MCP esteja conectado. Os papéis de arquitetura, segurança e qualidade não existem como agentes distintos: hoje há apenas `analyst` e `reviewer`.

---

## 11. Correções aplicadas nesta sessão

Aplicadas diretamente nos arquivos da pasta, sem commit. Preservam o fim de linha CRLF.

| Arquivo | Antes | Depois | Motivo |
|---|---|---|---|
| `pyproject.toml` (linha 11) | `authors = [{ name = "…", mail: "…" }]` | `authors = [{ name = "…", email = "…" }]` | TOML inválido; a chave prevista para autores é `email` (REP-03) |
| `.gitignore` | `mypy_cache/`; sem artefatos de build, cobertura e `.env` | `.mypy_cache/`; adicionados `build/`, `dist/`, `*.egg-info/`, `.coverage`, `htmlcov/`, `.env`, `.env.*` com exceção para `.env.example` | Padrão incorreto; `egg-info` chegou a ser versionado (REP-04) |
| `README.md` | "Estratégia de reposição: multirepo…" | "Estratégia de repositórios: multirepo…"; acrescentada uma linha com o caminho desta auditoria | Erro de digitação (DOC-09) |
| `CHANGELOG.md` | 3 itens | Acrescentados 4 itens que descrevem as mudanças desta sessão | Definition of Done |

Arquivos novos: `docs/audit/INITIAL_AUDIT.md`, `docs/IMPLEMENTATION_ROADMAP.md`, `docs/OPEN_DECISIONS.md`.

Validação: após a correção, `pyproject.toml` é lido por `tomllib`, e Ruff e Pytest passam da etapa de configuração. O build continua falhando por ausência de `src/` (PKG-01).

**Deliberadamente não alterado**, por depender de decisão pendente ou do estado do remoto:

- status e estrutura do README;
- `requires-python`, `license`, `dependencies` e `[project.scripts]` em `pyproject.toml`;
- `requirements.txt`;
- ARCHITECTURE, GOVERNANCE, SECURITY e CONTRIBUTING;
- qualquer coisa dentro de `.git`.

---

## 12. Pendências e próximos passos

Por prioridade:

1. **P0:** recuperar um clone íntegro (seção 3.6) e confirmar se houve perda.
2. **P1:** dar acesso ao código, pela pasta recuperada ou pelo remoto, e executar a auditoria complementar (seção 8.4; Fase 0 do roadmap).
3. **P1:** decidir D-00 (destino do scaffold), D-01 (repositórios) e D-02 (forma da Public API). Essas três decisões bloqueiam toda a implementação.
4. **P1:** verificar no GitHub o estado de `main`, os PRs abertos e os controles habilitados (D-19).
5. **P2:** executar a Fase 1 do roadmap (fundação de governança).
6. **P2:** registrar os ADRs e RFCs da Fase 2 antes de escrever código do Core.

A primeira entrega técnica recomendada após a recuperação é a **auditoria complementar do código**, seguida do ADR de D-01. Nenhuma implementação do Core deve começar antes disso.

---

## 13. Adendo — código adicionado à pasta

Depois deste relatório, os arquivos de trabalho foram adicionados à pasta e auditados. O resultado está em `docs/audit/CODE_AUDIT.md`. As seções 1 a 12 foram mantidas como registro do que era verificável na primeira execução; onde houver diferença, vale o relatório do código.

| Item deste relatório | Situação atualizada |
|---|---|
| REP-01 | Parcial: os arquivos de trabalho estão no disco, mas o Git continua sem `refs` e sem objetos. Além disso, 21 arquivos alterados depois do commit `6232d68` nunca foram commitados neste clone |
| PKG-01 | Resolvido: o wheel do Core constrói e instala |
| ARQ-02 | Reduzido: o código do Core não importa SQLAlchemy; a violação está só em `requirements.txt` |
| ARQ-03, ARQ-04, ARQ-05 | Confirmados e ampliados: pipeline padrão com 3 estágios; 18 de 38 módulos sem consumidor; o Core não executa a automação do consumidor |
| DOC-03 | Corrigido: `docs/adr/0000-template.md` existe no disco, fora da árvore do commit `6232d68`. Há três locais concorrentes para decisões e nenhum ADR escrito |
| DOC-04 | Confirmado: a CI roda apenas `pytest` |
| SEC-02 | Resolvido: revisão feita; os resultados estão nos achados SQL-02, SQL-03 e COD-11 do relatório do código |
| Seção 5 (matriz de status) | Substituída pela seção 9 do relatório do código |
| Seção 8.4 (roteiro) | Cumprido |
| Seção 3.6 (recuperação) | Continua válida. A origem provável da pasta é `C:\Users\guilherme.machado\orchestrator`, registrada em `.venv/pyvenv.cfg` |

---

## Apêndice A — Arquivos rastreados no index

Tamanho registrado no index para o arquivo do diretório de trabalho na última atualização (2026-07-06).

| Caminho | Bytes | No disco em 2026-11-11 |
|---|---:|:---:|
| `.github/CODEOWNERS` | 370 | não |
| `.github/ISSUE_TEMPLATE/adr_proposal.yml` | 1090 | não |
| `.github/ISSUE_TEMPLATE/bug_report.yml` | 1100 | não |
| `.github/ISSUE_TEMPLATE/config.yml` | 354 | não |
| `.github/ISSUE_TEMPLATE/feature_request.yml` | 849 | não |
| `.github/ISSUE_TEMPLATE/rfc.yml` | 1045 | não |
| `.github/PULL_REQUEST_TEMPLATE.md` | 764 | não |
| `.github/dependabot.yml` | 714 | não |
| `.github/labels.yml` | 2414 | não |
| `.github/workflows/ci.yml` | 456 | não |
| `.gitignore` | 219 | sim |
| `ARCHITECTURE.md` | 5074 | sim |
| `CHANGELOG.md` | 151 | sim |
| `CONTRIBUTING.md` | 421 | sim |
| `GOVERNANCE.md` | 3450 | sim |
| `LICENSE` | 1095 | sim |
| `README.md` | 1864 | sim |
| `SECURITY.md` | 4990 | sim |
| `assets/README.md` | 91 | não |
| `examples/README.md` | 238 | não |
| `examples/basic-spec.json` | 240 | não |
| `examples/sql-spec.json` | 1054 | não |
| `packages/README.md` | 99 | não |
| `packages/orchestrator_sql/README.md` | 1479 | não |
| `packages/orchestrator_sql/pyproject.toml` | 624 | não |
| `packages/orchestrator_sql/src/orchestrator_sql/__init__.py` | 406 | não |
| `packages/orchestrator_sql/src/orchestrator_sql/mappers/__init__.py` | 203 | não |
| `packages/orchestrator_sql/src/orchestrator_sql/mappers/table_mapper.py` | 6878 | não |
| `packages/orchestrator_sql/src/orchestrator_sql/query_executor.py` | 956 | não |
| `packages/orchestrator_sql/src/orchestrator_sql/schema_manager.py` | 1512 | não |
| `packages/orchestrator_sql/src/orchestrator_sql/sql_provider.py` | 11129 | não |
| `packages/orchestrator_sql/tests/conftest.py` | 159 | não |
| `packages/orchestrator_sql/tests/test_schema_manager.py` | 1299 | não |
| `packages/orchestrator_sql/tests/test_sql_provider.py` | 1181 | não |
| `pyproject.toml` | 583 | sim |
| `requirements.txt` | 98 | sim |
| `src/orchestrator_core.egg-info/PKG-INFO` | 2151 | não |
| `src/orchestrator_core.egg-info/SOURCES.txt` | 1303 | não |
| `src/orchestrator_core.egg-info/dependency_links.txt` | 2 | não |
| `src/orchestrator_core.egg-info/entry_points.txt` | 62 | não |
| `src/orchestrator_core.egg-info/top_level.txt` | 19 | não |
| `src/orchestrator_core/__init__.py` | 665 | não |
| `src/orchestrator_core/adapters/__init__.py` | 563 | não |
| `src/orchestrator_core/adapters/in_memory.py` | 2167 | não |
| `src/orchestrator_core/bootstrap.py` | 557 | não |
| `src/orchestrator_core/config_loader.py` | 1028 | não |
| `src/orchestrator_core/context.py` | 1143 | não |
| `src/orchestrator_core/events.py` | 1117 | não |
| `src/orchestrator_core/execution_engine.py` | 709 | não |
| `src/orchestrator_core/logging_service.py` | 736 | não |
| `src/orchestrator_core/main.py` | 1131 | não |
| `src/orchestrator_core/pipeline.py` | 1827 | não |
| `src/orchestrator_core/ports/__init__.py` | 754 | não |
| `src/orchestrator_core/ports/artifact.py` | 250 | não |
| `src/orchestrator_core/ports/cache.py` | 293 | não |
| `src/orchestrator_core/ports/configuration.py` | 319 | não |
| `src/orchestrator_core/ports/event.py` | 243 | não |
| `src/orchestrator_core/ports/infrastructure.py` | 305 | não |
| `src/orchestrator_core/ports/logging_port.py` | 252 | não |
| `src/orchestrator_core/ports/metrics.py` | 230 | não |
| `src/orchestrator_core/ports/metrics_port.py` | 318 | não |
| `src/orchestrator_core/ports/notification.py` | 304 | não |
| `src/orchestrator_core/ports/queue.py` | 275 | não |
| `src/orchestrator_core/ports/secrets.py` | 220 | não |
| `src/orchestrator_core/ports/storage.py` | 276 | não |
| `src/orchestrator_core/registry.py` | 909 | não |
| `src/orchestrator_core/runner/__init__.py` | 148 | não |
| `src/orchestrator_core/runner/base.py` | 843 | não |
| `src/orchestrator_core/runner_port.py` | 335 | não |
| `src/orchestrator_core/spec.py` | 2099 | não |
| `src/orchestrator_core/specification.py` | 120 | não |
| `src/orchestrator_core/stage/__init__.py` | 584 | não |
| `src/orchestrator_core/stage/base_stage.py` | 737 | não |
| `src/orchestrator_core/stage/execute_stage.py` | 398 | não |
| `src/orchestrator_core/stage/finalize_stage.py` | 372 | não |
| `src/orchestrator_core/stage/initialize_stage.py` | 390 | não |
| `src/orchestrator_core/stage/logging_stage.py` | 341 | não |
| `src/orchestrator_core/stage/shutdown_stage.py` | 363 | não |
| `src/orchestrator_core/utils.py` | 314 | não |
| `templates/README.md` | 101 | não |
| `tests/test_architecture_modules.py` | 1283 | não |
| `tests/test_core_runtime.py` | 2166 | não |

## Apêndice B — Como reproduzir as verificações

Sobre uma cópia da pasta, em um ambiente com Git e Python 3.11 ou superior:

```bash
git status                                   # verificação 1
python -c "import tomllib,sys; tomllib.load(open('pyproject.toml','rb'))"   # verificação 4
ruff check . && ruff format --check .        # verificação 5
mypy .                                       # verificação 6
python -m pytest                             # verificação 7
python -m pip wheel --no-deps -w dist .      # verificações 8 a 10
```

A leitura do index (verificações 2 e 3) exige que `.git` seja reconhecido como repositório. Na cópia de análise isso foi obtido criando um diretório `refs/` vazio; depois, `git ls-files --stage`, `git ls-files --debug` e `git hash-object` funcionam sem acessar objetos. **Não faça isso na pasta original.**

## Referências

- GitHub Docs — About GitHub Advanced Security: <https://docs.github.com/en/get-started/learning-about-github/about-github-advanced-security>
- GitHub Docs — GitHub security features: <https://docs.github.com/en/code-security/getting-started/github-security-features>
- Python Packaging User Guide — Writing your `pyproject.toml` (campo `license`): <https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license>
