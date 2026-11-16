# Changelog — orchestrator-notifications-smtp

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/). Versionamento semântico; antes da 1.0, uma versão menor pode quebrar compatibilidade.

## [Não lançado]

Versão 0.1.0 preparada em 2026-11-15 na branch local `feature/notifications-smtp`, sem push, tag nem release.

### Adicionado

- `SmtpChannel`: e-mail em texto simples com `starttls`, `tls` ou `none`, senha ou token OAuth 2.0 (`XOAUTH2`) por referência, tempo limite e tradução de erros ([RFC-0007](../../docs/rfc/0007-capability-de-notificacoes.md), seção 6, e resposta 1).
