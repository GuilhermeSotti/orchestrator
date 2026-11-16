# orchestrator-notifications

**Capability** de notificações da plataforma Orchestrator ([RFC-0007](../../docs/rfc/0007-capability-de-notificacoes.md), aceita em 2026-11-15). Define o contrato funcional (`Notifier`, `Notification`) e o port que os **Providers** de canal implementam (`NotificationChannel`). Não conhece nenhuma tecnologia: e-mail e Microsoft Teams entram como Providers (`orchestrator-notifications-smtp`, `orchestrator-notifications-teams`).

- Depende apenas de `orchestrator-core` 0.2 e da biblioteca padrão.
- Nada é enviado sem configuração explícita: o canal é nomeado pela automação, por `default_channels` ou pela tabela `lifecycle`.
- Avisos de ciclo de vida (`started`, `succeeded`, `failed`, `cancelled`, `timed_out`) exigem os dois atos da RFC-0007, seção 3: a tabela `lifecycle` e os estágios `NotifyStarted` e `NotifyOutcome`. Tabela sem estágio é recusada antes de a automação começar (resposta 6).
- Textos automáticos em português formal por padrão (resposta 3); o consumidor troca com `formatter=`. Logs e exceções continuam em inglês (ADR-0017).
- Falha de canal não muda o resultado: fica em log, na métrica `orchestrator.notifications.failed`, no evento `NotificationFailed` e no `DeliveryReport`. Com `required`, por canal ou por notificação (resposta 5), a falha lança `NotificationError`: no aviso de fim vira erro de teardown; no de início, impede a automação.
- Retry só para erros `retryable` (nada foi entregue), com `attempts` e `delay` por canal, dentro do orçamento de teardown. Sem limite de quantidade e sem agrupamento (resposta 4).
- Todo texto passa por `ctx.redact` antes de sair do processo. Destinatários ficam no canal, nunca na mensagem nem nos logs.

## Uso

```toml
# orchestrator.toml
[capabilities.notifications]
default_channels = ["operacao"]

[capabilities.notifications.lifecycle]
failed = ["operacao"]
timed_out = ["operacao"]

[capabilities.notifications.channels.operacao]
provider = "smtp"
host = "smtp.exemplo.interno"
sender = "automacao@exemplo.com"
to = ["operacao@exemplo.com"]
username = "automacao@exemplo.com"
password = "env:SMTP_PASSWORD"
```

```python
from orchestrator_core import ExecutionContext, RuntimeBuilder
from orchestrator_notifications import Notification, NotificationCapability, NotifyOutcome
from orchestrator_notifications_smtp import SmtpChannel

runtime = (
    RuntimeBuilder()
    .with_config_file("orchestrator.toml")
    .with_capability(NotificationCapability, providers={"smtp": SmtpChannel})  # registre primeiro
    .with_stage(NotifyOutcome(), after="finalize")
    .build()
)


def automacao(ctx: ExecutionContext) -> None:
    avisos = ctx.capability(NotificationCapability)
    avisos.send(Notification(subject="Lote processado", body="120 itens conferidos."))
```

Chaves de cada canal: `provider` (obrigatória), `required` (padrão `false`), `attempts` (padrão 1) e `delay` (segundos); as demais pertencem ao Provider. Chaves desconhecidas são erro.

## Decisões aplicadas

Como a RFC-0007 aceita e as respostas do responsável resolveram os pontos abertos da [reconciliação](../../docs/audit/RFC_RESPONSE_RECONCILIATION.md), seção 5:

| Ponto | Como ficou |
|---|---|
| C12, limite de volume | Sem limite e sem agrupamento (resposta 4); `max_per_execution` saiu do desenho |
| C13, `required` nos avisos de ciclo de vida | Vale a regra da seção 4 da RFC aceita: canal `required` no aviso de fim vira erro de teardown; no de início, impede a automação. A resposta 5 acrescenta `required=` por notificação em `send()` |
| C14, autenticação por token | Canais e credenciais por configuração e referência (resposta 1): token OAuth no SMTP (`XOAUTH2`) e URL do webhook do Teams como segredo. O canal real do ambiente não foi validado |
| C15, idioma | Textos automáticos em português formal (resposta 3), tratados como conteúdo para pessoas; código, logs e exceções continuam em inglês (ADR-0017) |

## Limites conhecidos

- Os estágios têm nomes fixos (`notify_started`, `notify_outcome`): uma única Capability de notificações com avisos de ciclo de vida por Runtime.
- Se uma Capability registrada antes desta falhar ao abrir, o aviso de fim não pode ser enviado (fica um aviso no log). Por isso, registre esta Capability primeiro.
- `send()` devolve uma tupla de `DeliveryReport`, um por canal, porque `default_channels` pode ter mais de um.

## Para autores de Providers

Implemente `NotificationChannel` (`from_config`, `verify`, `send`, `describe`) e passe na suíte `orchestrator_notifications.testing.NotificationChannelContract`. O mesmo módulo traz `InMemoryChannel`, para testes.

Licença: MIT.
