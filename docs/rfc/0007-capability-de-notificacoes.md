# RFC-0007 — Capability de notificações e Providers de e-mail e Microsoft Teams

| Campo | Valor |
|---|---|
| Status | Aceita em 2026-11-15 pelo responsável |
| Data | 2026-11-14 |
| Autor | Claude, a pedido do responsável |
| Decisor | Responsável pelo projeto (aceite registrado em [DECISIONS](../DECISIONS.md), seção 5) |
| Implementação | 2026-11-15: resposta 6 (`ExecutionContext.stages`) no Core 0.2.0; Capability `orchestrator-notifications` 0.1.0 na branch local `feature/notifications`, sem release. Como as respostas resolveram C12 a C15: [README do pacote](../../packages/orchestrator-notifications/README.md) |
| Item de escopo | 4 (notificações) |
| Relacionadas | [RFC-0004](0004-controles-reutilizaveis-escopo-e-sequencia.md), [RFC-0005](0005-core-0-2-subetapas-mascaramento-teardown-e-sinais.md) (2.1 e 2.2), [RFC-0006](0006-segredos-cofres-e-credenciais-de-providers.md), [ADR-0010](../adr/0010-retry-explicito.md) |

## 1. Problema e caso de uso

O responsável quer avisos de ciclo de vida (início, conclusão, falha) e avisos disparados pela lógica do consumidor, por canais como e-mail e Microsoft Teams, com ativação explícita e sem que a indisponibilidade de um canal altere em silêncio o resultado da automação.

O que se sabe do caso de uso termina aí. Destinatários, canais existentes, conteúdo e volume são perguntas abertas (seção 12).

Fatos do Core que condicionam o desenho ([SCOPE_DIAGNOSIS](../audit/SCOPE_DIAGNOSIS.md), seção 3.4): um assinante de `ExecutionFinished` não tem contexto, handles nem segredos; um finalizer recebe o desfecho calculado antes de `finalize`; um estágio depois de `finalize` vê os erros desse estágio e ainda alcança os handles; o texto do erro chega sem máscara; `ctx.retry` não funciona no teardown depois de prazo ou cancelamento.

## 2. Contrato funcional

Pacote `orchestrator-notifications`, que depende só do Core.

```python
from orchestrator_notifications import Notification, NotificationCapability, Severity


def automacao(ctx: ExecutionContext) -> None:
    avisos = ctx.capability(NotificationCapability)
    avisos.send(
        Notification(subject="<assunto>", body="<texto do consumidor>", severity=Severity.WARNING),
        channel="operacao",
    )
```

| Nome | Papel |
|---|---|
| `Notification` | `subject`, `body` (texto simples), `severity`, `facts` (pares nome e valor exibidos pelo canal), `kind` (identificador, como `execution.failed` ou um do consumidor) e `dedup_key` opcional |
| `Notifier.send(notification, *, channel=None)` | Envia ao canal nomeado ou aos `default_channels`; devolve um `DeliveryReport` |
| `DeliveryReport` | Canal, status (`sent`, `failed`, `skipped`), tentativas e erro mascarado |
| `Notifier.reports` | Todos os relatórios da execução |

O destinatário pertence ao canal, na configuração, e não à mensagem.

## 3. Avisos de ciclo de vida

Dois atos explícitos, os dois necessários:

1. **Composição**: instalar os estágios do pacote. `NotifyStarted` só é necessário para o aviso de início.
2. **Configuração**: a tabela `[capabilities.notifications.lifecycle]`, que lista os canais de cada status.

```python
builder.with_capability(NotificationCapability, providers=CANAIS)
builder.with_stage(NotifyStarted(), after="prepare_execution")
builder.with_stage(NotifyOutcome(), after="finalize")
```

Registrar a Capability não envia aviso de ciclo de vida, e os estágios sem a tabela também não. Um estágio instalado sem a Capability registrada é erro de configuração, que aparece na primeira execução. Status aceitos: `started`, `succeeded`, `failed`, `cancelled` e `timed_out`; os ausentes não geram aviso.

Limite conhecido: a tabela preenchida sem os estágios instalados não envia nada, e o Core não permite que uma Capability veja o pipeline para detectar o esquecimento. O caso fica documentado e é a pergunta 6 da seção 12.

| Escolha | Motivo |
|---|---|
| `NotifyStarted` depois de `prepare_execution` | Só avisa o início de execuções com Capabilities abertas e parâmetros válidos. É um estágio de preparação: se lançar erro, a automação não roda (seção 4) |
| `NotifyOutcome` depois de `finalize` | Já vê erros de finalizers e de liberação de recursos, e o próprio desfecho entra no registro da execução. Não vê falhas de `persist_logs` nem de `shutdown` |

Conteúdo: automação, Runtime, `execution_id`, status, duração e, em falha, tipo e mensagem mascarada do erro. Nunca parâmetros, retorno da automação, configuração ou traceback. O texto padrão é em inglês ([ADR-0017](../adr/0017-titularidade-licenca-idioma-visibilidade.md)); o consumidor pode entregar no registro uma função `formatter`, que monta a `Notification` com o texto e o idioma do negócio.

## 4. Falha, retry e idempotência

| Tema | Regra proposta |
|---|---|
| Falha de canal, padrão | Não muda o status. Fica em log (erro mascarado), na métrica `orchestrator.notifications.failed`, no `DeliveryReport` e no evento `NotificationFailed` |
| Canal com `required = true` | A falha lança `NotificationError`. No aviso de fim, vira erro de teardown: a execução bem-sucedida termina `failed`, com o erro no resultado e no registro. No aviso de início, falha a preparação e a automação não roda. Em `send()`, a exceção chega à automação |
| Retry | Nenhum por padrão. Por canal, `attempts` e `delay`. Só para erros `retryable`, isto é, quando o Provider sabe que nada foi entregue. Limitado pelo orçamento de teardown |
| Tempo limite | Obrigatório em todo Provider (`timeout`, padrão proposto 10 s): um canal travado não pode travar o teardown |
| Idempotência | Aviso de ciclo de vida: no máximo um por execução, status e canal. Falha ambígua, como tempo esgotado depois do envio, não é repetida: a preferência é não duplicar. A `dedup_key` é repassada ao Provider, que a usa onde o canal permitir |
| Volume | `max_per_execution` por canal para `send()`, padrão proposto 20; os excedentes ficam `skipped`, com aviso em log |

## 5. Port do Provider

`NotificationChannel`: `from_config(section)`, `verify()`, `send(notification, secrets)` e `describe()`, este sem credenciais nem endereços. Erros como `NotificationError`, subclasse de `ProviderError`, com `retryable`.

O pacote publica `orchestrator_notifications.testing`: um canal em memória e a suíte `NotificationChannelContract` (envio, tradução de erros, tempo limite, ausência de segredo em erros e em `describe()`).

## 6. Providers

**`orchestrator-notifications-smtp`**, só com a biblioteca padrão (`smtplib`, `email.message`). Chaves: `host`, `port`, `security` (`starttls`, `tls` ou `none`), `username` e `password` opcionais (a senha, por referência), `sender`, `to`, `cc`, `timeout`. Quebras de linha em cabeçalhos são recusadas. O `Message-ID` deriva da `dedup_key`.

Atenção: usuário e senha atendem a servidores internos e a outros provedores. No Exchange Online, a Microsoft informa que a autenticação básica do SMTP AUTH será desativada por padrão no fim de dezembro de 2026, com a data de remoção definitiva a anunciar no segundo semestre de 2027. Se o destino for o Exchange Online, o Provider precisa de OAuth ou de outro caminho de envio (pergunta 1).

**`orchestrator-notifications-teams`**, só com a biblioteca padrão (`urllib`). Envia uma requisição a um webhook de Workflows. A URL é um segredo e entra por referência (`webhook = "env:..."`). O formato do corpo precisa ser validado contra o fluxo do ambiente real. Os conectores do Office 365 no Teams não são alvo: a Microsoft programou a sua desativação para maio de 2026.

Enviar pelo Microsoft Graph exige registro de aplicativo e permissões a avaliar; seria outro Provider, se necessário.

## 7. Configuração

```toml
[capabilities.notifications]
default_channels = ["operacao"]

[capabilities.notifications.lifecycle]  # ausente: nenhum aviso de ciclo de vida
failed = ["operacao", "equipe"]
timed_out = ["operacao"]

[capabilities.notifications.channels.operacao]
provider = "smtp"
host = "smtp.exemplo.interno"
port = 587
security = "starttls"
username = "automacao@exemplo.com"
password = "env:SMTP_PASSWORD"
sender = "automacao@exemplo.com"
to = ["operacao@exemplo.com"]

[capabilities.notifications.channels.equipe]
provider = "teams"
webhook = "env:TEAMS_WEBHOOK_URL"
required = false
```

Chaves desconhecidas são erro, como nas demais tabelas reservadas.

## 8. Segurança e privacidade

- Todo texto passa por `ctx.redact` antes de sair do processo. Por isso a RFC-0005, 2.1, é pré-requisito.
- Senha de SMTP e URL de webhook só por referência de segredo.
- Endereços de destinatários são dados pessoais: não vão para logs; `describe()` mostra só o nome do canal e o host.
- Verificação de TLS ligada por padrão; `security = "none"` é explícito e gera aviso em log.
- A mudança envolve rede e exige revisão arquitetural de segurança no PR (`GOVERNANCE.md`, seção 9).

## 9. Compatibilidade

Pacotes novos. Dependem do Core 0.2: a parte 2.1 da RFC-0005 é obrigatória. Sem a parte 2.2, o retry no teardown usaria a função de módulo `retry()`, com limite próprio da Capability; funciona hoje, mas cada Capability passaria a ter o seu limite.

## 10. Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Assinante de `ExecutionFinished` | Vê o status final exato, mas não tem contexto, handles nem segredos. Exigiria segredos do escopo do Runtime (diagnóstico, L8.3) |
| Finalizer registrado pela Capability, sem estágios | Ligação mais simples, só por configuração, mas enxerga o desfecho calculado antes de `finalize`: pode anunciar sucesso de uma execução que termina `failed` |
| Estágio depois de `persist_logs` | Fica mais perto do status final, mas o resultado do aviso não entra no registro já entregue (RFC-0001, seção 9) |
| Notificações no Core | Contraria a ADR-0004 |
| `logging.handlers.SMTPHandler` | Mistura log técnico com aviso; sem política de falha, idempotência nem controle de volume |

## 11. Critérios de aceite e testes

Os da RFC-0004, seção 5 (E7.10 a E7.12), mais:

- matriz dos cinco status × canal comum ou `required` × canal disponível ou não, com o status final esperado em cada célula;
- o valor-sentinela não aparece em nenhuma mensagem, relatório, log ou evento;
- nenhum aviso de ciclo de vida sem os dois atos da seção 3;
- depois de `timed_out` e de `cancelled`, o aviso configurado é tentado;
- `check_capability_conformance` aprovada.

## 12. Perguntas abertas

1. Canais reais: servidor SMTP interno, Exchange Online (com qual autenticação), Teams com Workflows.

R: Os canais de notificação deverão ser parametrizáveis, permitindo que cada automação configure os canais que utilizará, conforme o ambiente e a necessidade do projeto. A autenticação também deverá permitir o uso de tokens, sem depender de credenciais ou configurações fixas na plataforma.

2. Quem recebe o quê, em quais status. O aviso de início é necessário?

R: Todos esses elementos deverão ser parametrizáveis. Cada automação poderá definir os destinatários, os tipos de notificação e os eventos ou status que deverão gerar avisos, incluindo a decisão de enviar ou não uma notificação de início.

3. Idioma e conteúdo mínimo; quem escreve o texto de negócio.

R: O idioma padrão deverá ser português do Brasil (PT-BR), utilizando textos formais para as mensagens automáticas da plataforma.

As notificações disparadas durante a execução da automação deverão ter seu conteúdo parametrizável, permitindo que cada projeto defina as mensagens conforme suas necessidades.

4. Volume esperado e necessidade de agrupar avisos.

R: Não deverá existir um limite predefinido de notificações por execução. Também não há necessidade de agrupar notificações. Cada aviso deverá ser enviado individualmente, conforme os eventos e as configurações definidos pela automação.

5. Algum aviso deve mudar o status quando falha (required)?

R: A obrigatoriedade deverá ser parametrizável para as notificações disparadas durante a execução. Cada automação poderá definir se uma falha no envio de determinada notificação deverá ou não afetar o resultado da execução.

6. Basta documentar o risco da tabela de ciclo de vida sem os estágios, ou o Core deve expor ao contexto a lista de estágios, para a Capability recusar a configuração no início da execução? A segunda opção muda a API pública (RFC-0002).

R: Escolho a segunda opção. O Core deverá disponibilizar ao contexto a lista de estágios configurados, permitindo que a Capability de notificações valide se os estágios necessários estão instalados. Caso exista uma configuração de notificações de ciclo de vida sem os respectivos estágios, a inconsistência deverá ser identificada e recusada no início da execução, antes que a automação seja iniciada.

**Condição de aceite.** Respostas 1 e 2 de um consumidor real.

## Referências externas (consultadas em 2026-11-13)

- Exchange Online, autenticação básica no SMTP AUTH, cronograma revisto em janeiro de 2026: blog da equipe do Exchange, <https://techcommunity.microsoft.com/blog/exchange/exchange-online-to-retire-basic-auth-for-client-submission-smtp/4114750>, e aviso MC786329 num espelho público do Message Center, <https://mc.merill.net/message/MC786329>.
- Conectores do Office 365 no Teams, desativação e migração para Workflows: aviso MC1181996, atualizado em abril de 2026, no mesmo espelho, <https://mc.merill.net/message/MC1181996>.

As duas datas devem ser conferidas no Message Center do próprio ambiente antes da implementação.
