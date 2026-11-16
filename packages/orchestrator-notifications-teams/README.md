# orchestrator-notifications-teams

**Provider** de Microsoft Teams da Capability `orchestrator-notifications` ([RFC-0007](../../docs/rfc/0007-capability-de-notificacoes.md), seção 6). Envia um Adaptive Card para um webhook de Workflows, só com a biblioteca padrão (`urllib`).

```toml
[capabilities.notifications.channels.equipe]
provider = "teams"
webhook = "env:TEAMS_WEBHOOK_URL"   # a URL é segredo: só referência
timeout = 10
```

- A URL nunca aparece em logs, erros nem em `describe()`. Uma URL escrita direto na configuração (`https://...`) é recusada.
- Só `https`; `http` apenas no endereço local, para testes. Redirecionamentos são recusados.
- Erros como `NotificationError`. `retryable` quando a conexão não chegou a ser feita ou quando a resposta foi 429, 502, 503 ou 504; sem resposta depois do envio, não repete (pode duplicar).
- O formato do cartão segue o modelo de Workflows "publicar em um canal quando uma solicitação de webhook for recebida". **Precisa ser validado contra o fluxo do ambiente real** (RFC-0007, seção 6): não foi testado contra o Teams. Os conectores do Office 365 não são alvo.

Testado com um servidor HTTP local feito com `http.server`.

Licença: MIT.
