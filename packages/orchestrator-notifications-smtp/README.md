# orchestrator-notifications-smtp

**Provider** de e-mail (SMTP) da Capability `orchestrator-notifications` ([RFC-0007](../../docs/rfc/0007-capability-de-notificacoes.md), seção 6). Usa só a biblioteca padrão (`smtplib`, `email.message`).

```toml
[capabilities.notifications.channels.operacao]
provider = "smtp"
host = "smtp.exemplo.interno"
port = 587                          # padrão: 587 starttls, 465 tls, 25 none
security = "starttls"               # starttls (padrão), tls ou none
username = "automacao@exemplo.com"
password = "env:SMTP_PASSWORD"      # referência; ou
token = "env:SMTP_OAUTH_TOKEN"      # token OAuth 2.0 (XOAUTH2)
sender = "automacao@exemplo.com"
to = ["operacao@exemplo.com"]
cc = []
timeout = 10
```

- Certificado e nome do servidor verificados por padrão; `security = "none"` envia em texto claro e gera aviso no log.
- Senha e token só por referência de segredo, resolvidos a cada envio. Com `token`, a autenticação é `XOAUTH2`; obter e renovar o token é papel do resolvedor do esquema (resposta 1 da RFC-0007). Para o Exchange Online, a autenticação básica do SMTP deixa de ser o padrão no fim de 2026 (RFC-0007, seção 6).
- Quebra de linha no assunto é recusada (injeção de cabeçalhos). O `Message-ID` deriva da `dedup_key`.
- Erros como `NotificationError`, sem endereços, senhas nem respostas do servidor. `retryable` só quando a falha ocorreu antes de entregar a mensagem ao servidor, ou com código 4xx.
- `describe()` mostra só host, porta e segurança.

Testado com um servidor SMTP local feito com `socketserver` e com objetos que substituem `smtplib`. Não testado contra um servidor real nem contra o Exchange Online.

Licença: MIT.
