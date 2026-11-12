# Governance

## Purpose

This document defines the engineering standards adopted by the Orchestrator platform.

Every contributor is expected to follow these guidelines.

---

# Repository Strategy

The platform adopts a Multi-Repository architecture.

Each repository represents a single responsibility.

Examples:

- orchestrator-core
- orchestrator-actions
- orchestrator-sql
- orchestrator-docker

Repositories evolve independently.

---

# Branch Strategy

Permanent branch

```
main
```

Temporary branches

```
feature/*
fix/*
hotfix/*
release/*
experiment/*
```

Direct commits to main are prohibited.

---

# Pull Requests

Every change must be submitted through a Pull Request.

PRs should contain:

- objective
- motivation
- testing evidence
- architectural impact
- related issues

---

# Versioning

Semantic Versioning is adopted.

MAJOR

Breaking changes.

MINOR

New features.

PATCH

Bug fixes.

---

# Architecture Decisions

Significant architectural changes require an ADR.

ADRs are stored under:

```
docs/adr/
```

---

# RFC Process

Large features begin with an RFC.

Implementation starts only after approval.

---

# Coding Standards

Mandatory:

- Type hints
- Ruff
- MyPy
- Pytest
- Docstrings
- Black-compatible formatting

---

# Testing Policy

Every new feature must include tests.

Minimum expectations:

- unit tests
- integration tests (when applicable)

Critical components should include stress tests.

---

# Dependencies

New dependencies require technical justification.

Selection criteria:

- maintenance
- community adoption
- security
- license compatibility
- release cadence

Abandoned libraries should not be adopted.

---

# Security

Mandatory:

- Secret Scanning
- Dependabot
- CodeQL
- Signed Releases
- Dependency Review

Secrets must never be committed.

---

# Documentation

Every public capability must contain documentation.

Every architectural decision must be documented.

Documentation is part of the Definition of Done.

---

# Capability Lifecycle

Every Capability follows the same lifecycle.

Proposal

↓

Architecture Review

↓

Implementation

↓

Testing

↓

Documentation

↓

Release

↓

Maintenance

↓

Deprecation

---

# Deprecation Policy

Deprecated features remain available for at least one minor release unless a security issue requires immediate removal.

Deprecations must be documented.

---

# Release Policy

Releases are created after feature completion.

Every release includes:

- Release Notes
- Changelog
- Migration Guide (if necessary)

---

# Issue Classification

Issues are categorized as:

- Bug
- Feature
- Capability
- Documentation
- Architecture
- Security
- Technical Debt

---

# Definition of Done

A task is considered complete only when:

- implementation finished
- tests passing
- documentation updated
- changelog updated
- review approved
- CI passing

---

# Long-Term Vision

The platform is designed to support:

- multiple teams
- hundreds of automation projects
- modular capabilities
- long-term maintenance
- enterprise governance

Every architectural decision should prioritize extensibility, maintainability and stability over short-term implementation speed.