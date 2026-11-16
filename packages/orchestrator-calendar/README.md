# orchestrator-calendar

**Capability** de calendários de dias úteis da [RFC-0011](../../docs/rfc/0011-calendarios-e-dias-uteis.md), só com a biblioteca padrão. Os feriados e as exceções são mantidos manualmente em arquivos (respostas 1 a 4), organizados em camadas com precedência.

```toml
[capabilities.calendar.calendars.operacao]
weekend = []                          # obrigatório; [] quando sábado e domingo são dias úteis
layers = ["feriados", "excecoes"]     # precedência: as camadas posteriores prevalecem
coverage = [2026, 2027]               # anos que o calendário declara completos
min_horizon_days = 30                 # opcional, padrão 0

[capabilities.calendar.sources.feriados]
provider = "file"                     # embutido
path = "calendarios/feriados.toml"    # relativo à pasta de trabalho

[capabilities.calendar.sources.excecoes]
provider = "file"
path = "calendarios/excecoes.csv"
delimiter = ";"                       # opcional: "," (padrão) ou ";"
```

```python
from datetime import date

from orchestrator_calendar import CalendarCapability
from orchestrator_core import ExecutionContext, RuntimeBuilder


def automacao(ctx: ExecutionContext) -> None:
    calendario = ctx.capability(CalendarCapability).get("operacao")
    hoje = calendario.today(ctx)
    proximo = calendario.add_business_days(hoje, 1)
    ctx.logger.info("próximo dia útil: %s (%s)", proximo, calendario.explain(proximo))


runtime = RuntimeBuilder().with_capability(CalendarCapability).build()
```

## Arquivos

Datas em `AAAA-MM-DD`; `type` é `holiday`, `business_day` ou `not_observed`; `reference` é opcional. Chaves ou colunas desconhecidas, datas inválidas, dia repetido na mesma camada e arquivo maior que `max_bytes` (padrão: 1 MiB) são erros, e a execução não começa.

```toml
[[entries]]
date = 2026-11-20
type = "holiday"
name = "Dia Nacional de Zumbi e da Consciência Negra"
reference = "Lei 14.759/2023"
```

```text
date;type;name;reference
2026-11-20;holiday;Dia Nacional de Zumbi e da Consciência Negra;Lei 14.759/2023
```

JSON: `{"entries": [{"date": "2026-11-20", "type": "holiday", "name": "..."}]}`. O CSV pode ter BOM, como os gravados por planilhas.

## Semântica

| Método | Resultado |
|---|---|
| `is_business_day(d)` | A entrada da última camada que tem o dia decide: `holiday` não é útil, `business_day` é útil, `not_observed` anula os feriados das camadas anteriores e deixa a regra do fim de semana decidir. Sem entrada, decide o fim de semana declarado |
| `add_business_days(d, n)` | Avança (`n > 0`) ou recua (`n < 0`) `n` dias úteis, sem contar `d`; `n = 0` é recusado |
| `roll(d, "forward" \| "backward")` | `d`, se for útil; senão, o próximo ou o anterior |
| `business_days_between(a, b, include_start=..., include_end=...)` | Contagem; os dois limites são obrigatórios |
| `holidays(ano)` | Feriados em vigor no ano, depois da precedência |
| `explain(d)` | Entrada que decidiu, com camada, fonte e versão |
| `today(ctx)` | Data de hoje no fuso da máquina (resposta 7) |

Qualquer dia fora de `coverage` lança `CalendarCoverageError`: um ano sem cadastro nunca é tratado como "sem feriados". A execução falha antes da automação se hoje, ou hoje mais `min_horizon_days`, estiver fora da cobertura.

Os cálculos citados na resposta 5:

| Cálculo | Chamada |
|---|---|
| Próximo dia útil depois de `d` | `add_business_days(d, 1)` |
| Próximo dia útil a partir de `d`, inclusive | `roll(d, "forward")` |
| Dia útil anterior a `d` | `add_business_days(d, -1)` |
| Último dia útil de um mês | `roll(<último dia do mês>, "backward")` |

## Rastreabilidade

Cada execução lê as fontes de novo no início: a edição manual de um arquivo vale para a próxima execução. A versão lida (`sha256:` do conteúdo) aparece no log, junto com a data de hoje e o fuso efetivo da máquina (`calendar 'operacao' loaded for 2026-11-16 (time zone of the machine: -03): ...`, C25), no evento `CalendarLoaded` e em `explain`.

## Decisões aplicadas e hipóteses

| Tema | Fonte | Aplicação |
|---|---|---|
| Feriados cadastrados manualmente | Respostas 1, 2 e 4 | Só a fonte em arquivo; o Provider de feriados padrão (biblioteca `holidays`) saiu do plano |
| Manutenção manual; responsáveis não definidos | Resposta 3 | Nenhum responsável fixo; a versão de cada camada fica registrada |
| Próximo e último dia útil | Resposta 5 | Tabela acima, com o contrato da RFC; "último dia útil" tem duas leituras (C24) e as duas estão cobertas, sem método novo |
| Sábado e domingo úteis | Resposta 6 | O fim de semana não tem padrão; para essa operação, `weekend = []` (C23) |
| Fuso da máquina | Resposta 7 | `today(ctx)` usa o fuso local; não há chave `timezone` nem dependência de `tzdata` |
| Fontes SQL e Excel | Seção 5 | Planejadas; o port `CalendarSource` e a suíte `orchestrator_calendar.testing.CalendarSourceContract` já existem para elas |

## Segurança

As fontes são entrada não confiável: tipos e datas validados, limite de tamanho, sem fórmulas nem código. Calendários não devem conter segredos nem dados pessoais. Mensagens de erro citam o caminho do arquivo e a entrada inválida.

Testado em Linux. Não testado em Windows.

Licença: MIT.
