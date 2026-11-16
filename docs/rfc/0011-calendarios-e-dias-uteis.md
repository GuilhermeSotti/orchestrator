# RFC-0011 — Calendários, feriados e dias úteis

| Campo | Valor |
|---|---|
| Status | Aceita em 2026-11-15 pelo responsável |
| Data | 2026-11-14 |
| Autor | Claude, a pedido do responsável |
| Decisor | Responsável pelo projeto (aceite registrado em [DECISIONS](../DECISIONS.md), seção 5) |
| Implementação | 2026-11-15: pacote `orchestrator-calendar` 0.1.0 (contrato da seção 3, fonte em arquivo da seção 5, critérios da seção 7), branch local `feature/calendar`, sem push. Respostas aplicadas: feriados manuais, sem o Provider `holidays` (1, 2, 4); fim de semana sem padrão, `weekend = []` para sábado e domingo úteis (6, C23); próximo e último dia útil pelo contrato existente, nas duas leituras de C24 (5); fuso da máquina, sem chave `timezone` (7). Fontes SQL e Excel: planejadas |
| Item de escopo | 9 (calendários, feriados e dias úteis) |
| Relacionadas | [RFC-0004](0004-controles-reutilizaveis-escopo-e-sequencia.md) (DS-1, DS-3, DS-6), [RFC-0010](0010-mapeamentos-compartilhados.md), [ADR-0016](../adr/0016-escopo-futuro.md) |

## 1. Problema

O responsável quer calendários reutilizáveis por várias automações, com feriados padrão e datas personalizadas; regras para dias úteis, feriados locais, exceções e critérios de atualização; e fontes como Excel e SQL por Providers, com validação e rastreabilidade.

Não existe nada parecido ([SCOPE_DIAGNOSIS](../audit/SCOPE_DIAGNOSIS.md), seção 3.9). A biblioteca padrão não traz feriados; `ctx.now()` devolve UTC e o Core não conhece o fuso do negócio.

Calendários mudam por lei: a Lei 14.759, de 21 de dezembro de 2023, declarou feriado nacional o 20 de novembro, observado em todo o país a partir de 2024. Um calendário sem dono e sem critério de atualização erra em silêncio.

Fora do escopo: agendamento de execuções (ADR-0016), horário de expediente e convenções financeiras de ajuste de datas, que só entram com caso de uso.

## 2. Modelo

| Conceito | Definição proposta |
|---|---|
| Calendário | Nome, dias de fim de semana, camadas em ordem e período de cobertura |
| Camada | Conjunto de entradas de uma fonte (feriados nacionais, de um estado, de um município, exceções de uma operação) |
| Entrada | Data, tipo, nome e, opcionalmente, a referência normativa (lei, decreto, comunicado) |
| Tipos de entrada | `holiday` (não é dia útil); `business_day` (é dia útil, mesmo caindo no fim de semana); `not_observed` (anula um feriado de camada anterior) |
| Precedência | Camadas posteriores prevalecem sobre as anteriores |
| Cobertura | Anos para os quais o calendário afirma estar completo |

Os dias de fim de semana **não têm valor padrão**: cada calendário os declara. Quais dias contam como úteis é regra do consumidor.

## 3. Contrato funcional

Pacote `orchestrator-calendar`, que depende só do Core e traz o Provider de arquivo. `BusinessCalendar` é um objeto imutável, utilizável também fora de uma execução (em testes, por exemplo).

```python
from datetime import date

from orchestrator_calendar import CalendarCapability


def automacao(ctx: ExecutionContext) -> None:
    calendario = ctx.capability(CalendarCapability).get("<calendário>")
    if not calendario.is_business_day(date(2026, 11, 20)):
        ctx.logger.info("motivo: %s", calendario.explain(date(2026, 11, 20)))
```

| Método | Semântica proposta |
|---|---|
| `is_business_day(d)` | Fim de semana declarado e entradas das camadas, na ordem de precedência |
| `add_business_days(d, n)` | Avança (`n > 0`) ou recua (`n < 0`) `n` dias úteis, sem contar `d`. `n = 0` é recusado: a intenção precisa ser explícita |
| `roll(d, direction)` | `d`, se for dia útil; senão, o próximo (`"forward"`) ou o anterior (`"backward"`) |
| `business_days_between(start, end, *, include_start, include_end)` | Conta dias úteis; os dois limites são parâmetros obrigatórios, sem padrão |
| `holidays(year)` | Entradas efetivas do ano, depois da precedência |
| `explain(d)` | Por que `d` é ou não dia útil: entradas que contribuíram, com camada, fonte e versão |
| `today(ctx)` | Data atual no fuso declarado do calendário (seção 6) |

Qualquer consulta fora do período de cobertura lança `CalendarCoverageError`. Tratar um ano desconhecido como "sem feriados" é o erro que esta regra evita.

## 4. Configuração

```toml
[capabilities.calendar.calendars.<calendário>]
weekend = ["saturday", "sunday"]
layers = ["<nacional>", "<estadual>", "<exceções>"]
coverage = [2025, 2028]
timezone = "America/Sao_Paulo"

[capabilities.calendar.sources.<nacional>]
provider = "holidays"
country = "BR"

[capabilities.calendar.sources.<estadual>]
provider = "holidays"
country = "BR"
subdivision = "<UF>"

[capabilities.calendar.sources.<exceções>]
provider = "file"
path = "calendarios/<exceções>.toml"
```

Como nos demais pacotes, só os Providers passados em `providers=` na composição podem ser escolhidos pela configuração.

## 5. Providers

| Provider | Pacote | Versão registrada | Observações |
|---|---|---|---|
| Arquivo (TOML, CSV, JSON) | `orchestrator-calendar` (embutido) | SHA-256 do conteúdo | Datas ISO; entradas repetidas na mesma camada são erro |
| Feriados padrão | `orchestrator-calendar-holidays` | Versão da biblioteca `holidays` | Biblioteca de licença MIT. Para o Brasil, cobre os 26 estados e o Distrito Federal, a capital paulista como subdivisão municipal, uma categoria de feriados opcionais e um calendário de mercado (BVMF, descrito como igual ao da ANBIMA). Outros municípios ficam em camadas próprias |
| SQL | `orchestrator-calendar-sql` | Coluna ou consulta de versão indicada pelo consumidor | Tabela e colunas de um mapa do consumidor; nenhum nome fixo (RFC-0004, DS-1) |
| Excel | `orchestrator-calendar-excel` | SHA-256 do arquivo | Mesmas decisões de leitura da [RFC-0010](0010-mapeamentos-compartilhados.md), seção 5. Se mapeamentos e calendários lerem Excel, é o segundo uso previsto na RFC-0004, DS-6: avaliar então a Capability Excel |

## 6. Fuso horário

"Hoje" depende do fuso do negócio. `today(ctx)` converte `ctx.now()` para o fuso declarado no calendário, com `zoneinfo`. Em Windows, `zoneinfo` depende do pacote `tzdata`, de terceiros, que entraria como dependência condicional (`tzdata; sys_platform == "win32"`) e sob a política da RFC-0004, DS-3. Alternativa só com a biblioteca padrão: um deslocamento fixo (`utc_offset = "-03:00"`), correto enquanto o fuso não tiver horário de verão.

## 7. Critérios de atualização e rastreabilidade

1. Cada camada tem um responsável nomeado na sua fonte (pergunta 3).
2. A carga falha se a cobertura não incluir o ano corrente e o horizonte configurado (`min_horizon_days`). O aviso aparece antes do problema, não no dia.
3. Mudanças em camadas de arquivo passam por revisão (Pull Request num pacote de dados da organização, por exemplo); em SQL, pelo controle de alterações do próprio banco.
4. Atualizar a biblioteca `holidays` pode mudar resultados: a versão fica fixada no lock e a atualização é uma mudança revisada, com testes do consumidor para datas conhecidas.
5. Fonte e versão de cada camada aparecem no log da execução e no evento `CalendarLoaded`; `explain(d)` mostra a origem de cada decisão.

## 8. Segurança

Calendários não contêm segredos nem dados pessoais. As fontes são entrada não confiável: validação de datas, tipos e repetições; limite de tamanho; nada de fórmulas ou macros no Excel; identificadores SQL validados e valores como parâmetros.

## 9. Compatibilidade

Pacotes novos; o Core não muda. O Provider de feriados padrão e, em Windows, o fuso trazem dependências de terceiros (DS-3).

## 10. Alternativas consideradas

| Alternativa | Avaliação |
|---|---|
| Usar `holidays` diretamente em cada automação | Funciona hoje; não resolve exceções locais compartilhadas, cobertura nem rastreabilidade |
| Calendário como mapeamento genérico (RFC-0010) | Os dados cabem, mas a semântica (fim de semana, precedência, contagem, cobertura) se repetiria em cada consumidor |
| Feriados calculados pela plataforma (Páscoa e datas móveis) sem biblioteca | Possível com a biblioteca padrão, mas mantém regras de calendário oficial dentro da plataforma, o que exige acompanhar mudanças de lei |
| Uma tabela única de feriados imposta a todos | Contraria o pedido e a ADR-0019 |

## 11. Perguntas abertas

1. Jurisdições: nacional, estadual, municipal; quais municípios.

R: Todos os feriados serão cadastrados manualmente

2. Calendário civil, bancário ou ambos; tratamento dos pontos facultativos.

R: Todos os feriados serão cadastrados manualmente

3. Quem mantém cada camada de exceções.

R: A manutenção dos calendários deverá ser realizada manualmente, incluindo a revisão e a atualização das datas e informações de cada calendário.

As alterações deverão acompanhar as necessidades de cada calendário. A definição dos responsáveis específicos pela manutenção de cada camada ainda não foi estabelecida.

4. Horizonte necessário, em anos.

R: Todos os feriados serão cadastrados manualmente

5. Cálculos usados hoje: próximo dia útil, soma de dias úteis, contagem entre datas, outros.

R: Captura de próximo dia útimo, ultimo dia útil

6. Sábado é dia útil em alguma operação?

R: Em todas as operações, Sábado e domingo será dia útil

7. Fuso do negócio e se as automações rodam perto da meia-noite.

R: Fuso horário da maquina em execução

**Condição de aceite.** Respostas 1, 2 e 5 de um consumidor real.

## 12. Critérios de aceite e testes

Os da RFC-0004, seção 5 (E7.21 e E7.22), mais:

- tabela de casos de fronteira: virada de ano, feriado no fim de semana, exceção que anula feriado, dia útil forçado no sábado, `n` negativo;
- consulta fora da cobertura sempre falha;
- `explain` aponta a camada e a versão corretas;
- o mesmo calendário, definido em arquivo e em SQL, dá os mesmos resultados (suíte de conformidade do port);
- `check_capability_conformance` aprovada.

## Referências externas (consultadas em 2026-11-14)

- Lei 14.759/2023: Agência Senado, <https://www12.senado.leg.br/noticias/materias/2023/12/22/dia-da-consciencia-negra-se-torna-feriado-nacional>.
- Biblioteca `holidays` no PyPI (versão 0.108, de 2 de novembro de 2026; Python 3.11 ou superior; MIT): <https://pypi.org/project/holidays/>. O suporte a Python 3.15 precisa ser verificado na entrega.
