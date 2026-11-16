# orchestrator-records-file

Destinos em arquivo da [RFC-0009](../../docs/rfc/0009-destinos-de-registros-e-logs.md), só com a biblioteca padrão:

- `JsonLinesRecordSink`: **Provider** do port `ExecutionRecordSink` do Core. Grava o registro de cada execução numa linha JSON (seção 2.2).
- `TextLogHandler`: handler do módulo `logging`. Grava os logs técnicos em arquivos TXT organizados por pastas, com retenção (resposta 1).

```python
import logging

from orchestrator_core import RuntimeBuilder
from orchestrator_core.logs import configure_logging
from orchestrator_records_file import JsonLinesRecordSink, TextLogHandler

configure_logging("INFO")  # console, como antes
logging.getLogger().addHandler(TextLogHandler(r"C:\Logs\vendas"))
sink = JsonLinesRecordSink(r"C:\Registros\vendas", prefix="vendas", retention_days=180)
runtime = RuntimeBuilder().with_record_sink(sink).build()
```

As pastas raiz precisam existir. O consumidor escolhe os caminhos na composição, por exemplo a partir da própria configuração; o port do Core não tem tabela de configuração.

## Logs em TXT

Caminho padrão, relativo à pasta raiz (`DEFAULT_LOG_PATH`):

```text
{stage}/{step}/{year}/{month}/{day}/{hostname}_{user}_{pid}.txt
```

Exemplo: `C:\Logs\vendas\execute_automation\carregar_pedidos\2026\11\15\MAQUINA01_robo_4242.txt`.

| Parâmetro | Padrão | Efeito |
|---|---|---|
| `path` | `DEFAULT_LOG_PATH` | Modelo do caminho. Marcadores: `automation`, `execution_id`, `stage`, `step`, `year`, `month`, `day`, `hostname`, `user`, `pid` |
| `retention_months` | `6` | Meses mantidos; `None` desliga a remoção |
| `utc` | `True` | Datas das pastas e horários das linhas em UTC (terminam em `Z`); `False` usa o horário local da máquina |
| `level` | todos | Nível mínimo |
| `max_open_files` | `8` | Arquivos abertos ao mesmo tempo no processo |

- Linhas fora de uma subetapa, ou fora de uma execução, usam `_` no lugar do valor ausente.
- Valores viram nomes portáteis: só letras, dígitos, `_`, `.` e `-`; `..` nunca chega ao caminho; nomes reservados do Windows (`aux`, `con`, `nul`...) ganham `_` na frente. O caminho nunca sai da pasta raiz.
- As linhas usam `TEXT_FORMAT` do Core, com `execution_id` e estágio. O handler instala `ExecutionContextFilter` e `RedactingFilter`: segredos resolvidos pelo Runtime são mascarados.
- Retenção: na primeira linha de cada dia, o processo remove os arquivos que seguem o modelo e são de dias anteriores a "hoje menos `retention_months` meses", e depois as pastas que ficaram vazias. Arquivos fora do modelo e links simbólicos nunca são removidos. O modelo precisa ter `{year}`, `{month}` e `{day}` para a retenção funcionar.
- Um erro de escrita vai para `logging.Handler.handleError` e nunca chega à automação.

## Registros em JSON Lines

Uma linha por execução com `record.to_dict()`, já mascarado pelo Runtime e sem parâmetros nem retorno da automação. Arquivo por dia (UTC, de `finished_at`): `<prefixo>-AAAA-MM-DD-<host>-<pid>.jsonl`.

| Parâmetro | Padrão | Efeito |
|---|---|---|
| `prefix` | `records` | Início do nome dos arquivos |
| `per_process` | `True` | Host e PID no nome; com `False`, `<prefixo>-AAAA-MM-DD.jsonl`, e só um processo pode gravar com esse prefixo |
| `retention_days` | desligada | Remove, no primeiro registro de cada dia, os arquivos do prefixo de dias anteriores a "hoje menos `retention_days`", de qualquer processo |
| `fsync` | `False` | `os.fsync` depois de cada registro |

Uma falha de escrita lança exceção; o Runtime a registra em log como aviso e na métrica `orchestrator.record_sink.errors`, e o status da execução não muda (resposta 6).

## Vários processos

Com o PID no nome (padrão nos dois destinos), cada processo grava os próprios arquivos e vários processos podem escrever na mesma pasta ao mesmo tempo, inclusive em máquinas diferentes com uma pasta compartilhada (resposta 5). A biblioteca padrão não oferece trava de arquivo portátil entre processos: tirar o PID do nome só é seguro com um processo por arquivo.

O teste `tests/test_multiprocess.py` inicia quatro processos reais que gravam ao mesmo tempo nas mesmas pastas, e confere que nenhuma linha se perde ou se mistura e que as remoções simultâneas da retenção não falham. Executado em Linux; não executado em Windows nem em pasta de rede.

## Decisões aplicadas e hipóteses

| Tema | Fonte | Aplicação |
|---|---|---|
| Retenção dos logs, padrão de 6 meses | Resposta 1 | `retention_months=6` |
| Pasta inicial parametrizável | Resposta 1 | Parâmetro `root` |
| Estrutura `etapa/subetapa/ano/mes/dia/[Hostname]_[UserMachine].txt` | Resposta 1 | **Hipótese** (C19 da [reconciliação](../../docs/audit/RFC_RESPONSE_RECONCILIATION.md)): etapa é o estágio do pipeline e subetapa é a subetapa aberta (`ctx.step`). O modelo é configurável |
| Vários processos na mesma pasta | Resposta 5 | **Hipótese** (C16): um arquivo por processo, com o PID no nome, em vez de `[Hostname]_[UserMachine].txt` compartilhado |
| Linhas fora de subetapa | C19, em aberto | Pasta `_` |
| Quem remove os vencidos | C19, em aberto | O próprio destino, na primeira gravação de cada dia |
| Falha ao gravar o registro | Resposta 6, C17 | Tratada no Core 0.2.0; o destino só lança a exceção |
| Volume parametrizável | Resposta 4 | Nenhum limite fixo de linhas ou execuções |
| LGPD | Resposta 3 | Segredos mascarados; dados pessoais não são detectados e não devem ser registrados pelo consumidor (`SECURITY.md`, seção "Logs") |
| Registros e logs em SQL | Seção 2.3 | Fora deste pacote (E7.14, bloqueada) |

## Segurança

- Arquivos e pastas são criados com as permissões padrão do processo. Restrinja a pasta raiz à conta que executa as automações.
- Dados pessoais vindos de mensagens de exceção de terceiros podem chegar aos logs e aos registros: o mascaramento só cobre segredos resolvidos.

Licença: MIT.
