# Processo de release

Decisões: [RFC-0002](../rfc/0002-escopo-do-mvp-e-api-publica.md) (distribuição) e [ADR-0018](../adr/0018-convencoes-de-commit-branch-e-versao.md) (versões e tags).

1. Atualize a versão em `packages/<pacote>/src/<modulo>/_version.py` e a seção do `CHANGELOG.md` do pacote, por PR.
2. Confira a matriz em `docs/COMPATIBILITY.md` e as faixas de dependência dos pacotes que dependem do que mudou.
3. Depois do merge, crie a tag anotada no commit de `main`:

   ```powershell
   git tag -a orchestrator-core/v0.1.1 -m "orchestrator-core 0.1.1"
   git push origin orchestrator-core/v0.1.1
   ```

4. O workflow `release.yml` constrói wheel e sdist do pacote da tag, com build reproduzível, e cria a release no GitHub com os artefatos e o hash SHA-256 de cada um.
5. Publicar em índice de pacotes não faz parte do processo atual e exige RFC e autorização do responsável.

Antes da 1.0, uma versão menor pode quebrar compatibilidade; descreva a migração no CHANGELOG.
