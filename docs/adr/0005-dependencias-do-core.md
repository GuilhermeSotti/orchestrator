# ADR-0005 — Dependências do Core: somente a biblioteca padrão

| Campo | Valor |
|---|---|
| Status | Aceito |
| Data | 2026-11-12 |
| Decisão | D-04 |
| Decisor | Claude, por delegação explícita do responsável pelo projeto (2026-11-12) |

## Contexto

SECURITY afirma que o Core nunca depende diretamente de bibliotecas de terceiros; a stack-alvo lista Pydantic (DOC-06). O `requirements.txt` do scaffold listava SQLAlchemy como dependência do Core (ARQ-02). A recomendação anterior era aceitar Pydantic como única dependência, restrita às fronteiras de dados.

Durante o desenho, as necessidades de validação do Core se mostraram pequenas: a tabela `[runtime]` tem cinco chaves; a validação de parâmetros e das configurações das Capabilities pertence ao consumidor e às próprias Capabilities.

## Decisão

1. O Core depende só da biblioteca padrão. Um teste (`test_core_imports_only_the_standard_library`) falha se qualquer módulo do Core importar outra coisa.
2. A validação de configuração do Core usa `ConfigSection`, com conversões explícitas e mensagens que citam a chave completa.
3. A validação de parâmetros é delegada a um callable fornecido pelo consumidor (`parameters_validator`). Pydantic é o caminho recomendado (`parameters_validator=Modelo.model_validate`), coberto por teste.
4. Capabilities e Providers podem ter dependências próprias, com justificativa no PR. A Capability SQL e o Provider SQLite não precisaram de nenhuma.

Esta decisão substitui a recomendação anterior (Pydantic no Core) pelos motivos acima.

## Alternativas consideradas

- **Pydantic como única dependência do Core.** Validação robusta, mas impõe uma dependência compilada a todo consumidor e acopla o Core às versões maiores do Pydantic, para validar cinco chaves.
- **Pydantic em todos os modelos do Core.** Acoplamento ainda maior dos contratos.

## Consequências

- Nenhum conflito de versão entre o Core e o consumidor; instalação possível sem acesso a índice de pacotes além do próprio Core.
- A frase de SECURITY sobre bibliotecas de terceiros continua verdadeira.
- Pydantic permanece na stack-alvo como biblioteca recomendada para consumidores e Capabilities.

## Referências

- `packages/orchestrator-core/tests/test_public_api.py`; `test_pydantic_models_work_as_parameter_validators`.
