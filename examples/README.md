# Exemplos

Projetos consumidores reais, com `pyproject.toml` próprio. Na CI, são instalados a partir dos wheels construídos e executados de ponta a ponta.

| Exemplo | Usa | Demonstra |
|---|---|---|
| [hello-automation](hello-automation) | `orchestrator-core` | Automação, parâmetros validados, configuração, workspace, logs correlacionados |
| [sales-report](sales-report) | Core, `orchestrator-sql`, `orchestrator-sqlite` | Capability registrada por classe, banco escolhido pela configuração, transação e consultas parametrizadas |
| [batch-check](batch-check) | Core, `orchestrator-notifications`, canais SMTP e Teams | Avisos de ciclo de vida, notificação de negócio, canal escolhido pela configuração; na CI, envia a um servidor SMTP local |
