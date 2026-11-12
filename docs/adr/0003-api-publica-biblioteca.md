# ADR-0003 — Forma da Public API: biblioteca Python primeiro

| Campo | Valor |
|---|---|
| Status | Aceito |
| Data | 2026-11-12 |
| Decisão | D-02 |
| Decisor | Claude, por delegação explícita do responsável pelo projeto (2026-11-12) |

## Contexto

Não estava definido como um projeto consumidor usa o Orchestrator. O scaffold lia uma spec JSON por uma CLI, mas a spec só tinha nomes de tarefas, sem ligação com código (COD-01, COD-12).

## Decisão

1. O Orchestrator é usado como biblioteca. O consumidor compõe o Runtime em Python com `RuntimeBuilder` e entrega a automação como um callable que recebe o `ExecutionContext`:

   ```python
   runtime = RuntimeBuilder().with_config_file("orchestrator.toml").build()
   result = runtime.run(conciliar_faturas, parameters={"dia": "2026-11-12"})
   result.raise_for_status()
   ```

2. O Core não tem interpretador de spec nem CLI. Cada projeto consumidor escreve a sua linha de comando, se precisar (os exemplos mostram como, com `argparse`).
3. Uma camada declarativa (spec ou CLI genérica) só pode surgir como pacote separado, por RFC, com schema versionado e modelo de segurança para importação dinâmica.

## Alternativas consideradas

- **Spec declarativa interpretada pelo Core.** Desloca lógica de negócio para um formato sem tipos nem testes e tende a virar o workflow engine listado como evolução futura (ADR-0016).
- **As duas formas no Core.** Dobra a superfície pública antes de a primeira estar validada.

## Consequências

- A lógica de negócio continua sendo código do consumidor, tipado e testado com as ferramentas comuns.
- A superfície pública é a lista da RFC-0002, verificada por teste.

## Referências

- RFC-0002; exemplos em `examples/`.
