# CLAUDE.md — instruções para assistentes de IA neste repositório

## Contexto

Orchestrator: plataforma modular de automação em Python. O Core fornece infraestrutura técnica (Runtime, pipeline de oito estágios, Execution Context, configuração, segredos, logging, eventos, métricas, retry, cancelamento); a lógica de negócio fica nos projetos consumidores. Visão e regras: `ARCHITECTURE.md`, `GOVERNANCE.md`, `SECURITY.md`. Todas as decisões tomadas estão em `docs/DECISIONS.md`, com ADRs em `docs/adr/` e RFCs em `docs/rfc/`.

## Estrutura

- `packages/orchestrator-core`: Core, somente biblioteca padrão (ADR-0005). API pública fixada pela RFC-0002 e por `tests/test_public_api.py`.
- `packages/orchestrator-sql`: Capability SQL; depende só do Core.
- `packages/orchestrator-sqlite`: Provider SQLite; depende da Capability e do Core.
- `examples/`: projetos consumidores de exemplo.
- `tools/`: verificação de links, fronteiras entre pacotes e build reproduzível.
- Os pacotes incubam aqui durante a série 0.x; a topologia-alvo é multirrepositório (ADR-0001). Não junte nem separe pacotes sem ADR.

## Comandos

```text
pip install -r requirements/dev.txt
pip install -e packages/orchestrator-core -e packages/orchestrator-sql -e packages/orchestrator-sqlite -e examples/hello-automation -e examples/sales-report
ruff check . && ruff format --check . && mypy && pytest
python tools/build_packages.py --check
python -m tools.e2e   # instala os wheels num ambiente limpo e roda os exemplos
```

O `pyproject.toml` da raiz configura as ferramentas e não é pacote. Pytest roda a partir das fontes (`pythonpath`), sem instalação.

## Regras

1. Vocabulário: Capability e Provider não são sinônimos (ARCHITECTURE, seção 2).
2. O Core não importa bibliotecas de terceiros nem pacotes de Capabilities; os testes de fronteira falham se isso acontecer.
3. Mudança de contrato público exige atualizar a RFC-0002, o teste da lista pública, o CHANGELOG do pacote e avaliar compatibilidade (`docs/COMPATIBILITY.md`).
4. Mudança arquitetural significativa exige ADR; funcionalidade grande exige RFC aceita antes do código.
5. Código, docstrings e mensagens em inglês; documentação narrativa em português (ADR-0017).
6. Conventional Commits com descrição em português; squash merge; tags `<distribuição>/v<versão>` (ADR-0018).
7. Nunca afirme que testes, lint, tipos ou CI passaram sem executar e ver o resultado.
8. Segredos nunca em código, configuração versionada ou logs; use referências (`env:`, `file:`).
9. Sem autorização explícita do responsável: não faça commit, push, merge, release, publicação de pacote, nem altere configurações do GitHub.

## Estado

Veja `docs/IMPLEMENTATION_ROADMAP.md` (situação de cada entrega) e `docs/DECISIONS.md` (pendências do responsável).
