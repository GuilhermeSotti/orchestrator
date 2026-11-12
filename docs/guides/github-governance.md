# Governança GitHub

Este guia consolida a postura mínima de governança do repositório para um cenário enterprise-ready.

## 1. Branches e proteção

- Branch principal: main
- Branches de trabalho: feature/*, fix/*, hotfix/* e release/*
- Nunca realizar commits diretos em main
- Configurar branch protection ou rulesets para main, release/* e hotfix/*

## 2. Regras recomendadas

- Require pull request before merging
- Requerer 1 aprovação inicial, evoluindo para 2 conforme a equipe crescer
- Dismiss stale approvals
- Require conversation resolution
- Require status checks
- Require branches to be up to date
- Restrict force pushes
- Restrict deletions
- Linear history

## 3. Ownership e revisão

- O arquivo .github/CODEOWNERS define os proprietários por área
- A revisão deve seguir o domínio técnico afetado

## 4. Issues e pull requests

- Bug reports, feature requests, RFCs e ADR proposals devem ser criados por formulários estruturados
- Todo pull request deve usar o template padrão e incluir contexto, impacto, testes e checklist

## 5. Organização do trabalho

- Usar um projeto Kanban com as colunas Backlog, Ready, In Progress, Review, Testing e Done
- Usar milestones por versão semver, por exemplo v0.1.0, v0.2.0, v1.0.0
- Ativar Discussions para anúncios, ideias, perguntas, arquitetura, RFCs e showcases
- Criar releases com contexto de planejamento antes de publicar

## 6. Convenções de nomenclatura

- Features: feature/hexagonal-core
- Correções: fix/config-loader
- Hotfix: hotfix/security-patch
- Releases: release/0.1.0
