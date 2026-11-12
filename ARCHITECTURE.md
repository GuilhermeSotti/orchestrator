# Architecture

## Overview

Orchestrator is a modular automation platform designed to standardize the complete lifecycle of automation development and execution.

The platform is technology-agnostic and is not coupled to any specific automation framework, execution engine, database, cloud provider or infrastructure.

Its purpose is to provide a common runtime capable of orchestrating multiple technologies through independent modules called Capabilities.

The project follows a modular architecture based on:

- SOLID
- Clean Architecture
- Hexagonal Architecture (Ports & Adapters)
- Dependency Injection
- Strategy Pattern
- Factory Pattern
- Builder Pattern
- Event-Driven Architecture
- Plugin Architecture

---

# Vision

The Orchestrator should become the central runtime responsible for the execution of automation projects.

Business logic must remain inside the consumer project.

The platform provides only technical infrastructure.

Examples include:

- execution lifecycle
- dependency provisioning
- configuration
- logging
- metrics
- retry
- execution context
- events
- monitoring
- dependency management
- providers
- capabilities

---

# Design Principles

The platform is guided by the following principles.

## Modularity

Every major feature must be developed as an independent package.

The Core should remain as small as possible.

---

## Extensibility

New technologies must be added without changing the Core.

Examples:

- SQL
- PostgreSQL
- MySQL
- Docker
- Browser
- Excel
- Playwright
- Selenium
- BotCity
- OpenTelemetry

---

## Low Coupling

Modules communicate through interfaces.

The Core never depends on concrete implementations.

---

## Convention over Configuration

The platform should provide intelligent defaults while allowing full customization.

---

## Explicit Dependencies

Every dependency must be declared.

No hidden runtime dependencies.

---

## Testability

Every component must be independently testable.

Dependency Injection is preferred over static objects.

---

# High Level Architecture

```
Automation Project
        │
        ▼
Public API
        │
        ▼
Execution Runtime
        │
──────────────────────────────────────────────
Execution Pipeline

Execution Context

Configuration

Dependency Injection

Event Bus

Logging

Metrics

Retry

Lifecycle

Capability Registry
──────────────────────────────────────────────
        │
        ▼
Ports
        │
        ▼
Capabilities
        │
        ▼
Providers
```

---

# Execution Lifecycle

The Runtime is responsible for orchestrating every execution.

Current lifecycle:

```
Initialize

↓

Provision Dependencies

↓

Prepare Environment

↓

Prepare Execution

↓

Execute Automation

↓

Finalize

↓

Persist Logs

↓

Shutdown
```

The lifecycle is implemented as a pipeline.

New stages may be introduced without modifying existing ones.

---

# Capabilities

Capabilities are modular components that extend the Runtime.

Examples:

- SQL
- Docker
- Browser
- Filesystem
- HTTP
- Excel
- PDF
- OCR
- Queue
- Email
- Notification
- Secrets
- JavaScript

Capabilities are discovered through the Capability Registry.

The Runtime never references concrete implementations directly.

---

# Providers

Providers implement external integrations.

Examples:

- SQLite
- SQL Server
- PostgreSQL
- MySQL
- Docker
- Azure
- AWS
- Local Filesystem
- Elastic
- OpenTelemetry

Providers must implement contracts defined by the Core.

---

# Package Organization

The platform follows a modular multi-repository strategy.

Examples:

- orchestrator-core
- orchestrator-actions
- orchestrator-sql
- orchestrator-postgres
- orchestrator-mysql
- orchestrator-excel
- orchestrator-browser
- orchestrator-playwright
- orchestrator-docker
- orchestrator-http

---

# Dependency Rule

Dependencies always point inward.

```
Providers
↓

Capabilities
↓

Core

↓

Public API
```

The Core must never depend on infrastructure.

---

# Compatibility

Public APIs are considered stable.

Breaking changes require a major version.

Internal modules may evolve independently.

---

# Technology Stack

Current target:

- Python 3.13+
- Pydantic
- PyProject
- Ruff
- MyPy
- Pytest

Additional technologies may be introduced through Capabilities.

---

# Future Evolution

The architecture is intentionally open for future expansion, including:

- distributed execution
- remote agents
- cloud execution
- plugin marketplace
- package registry
- orchestration dashboards
- workflow engine
- scheduling
- AI-assisted automation