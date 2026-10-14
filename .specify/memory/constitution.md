<!--
Sync Impact Report:
- Version change: [TEMPLATE] -> 1.0.0
- Ratified: 2026-10-14
- Core Principles established:
  - I. The Core Architecture: Use Cases vs. Context Services (NON-NEGOTIABLE)
  - II. Ports & Adapters Isolation (Hexagonal Architecture)
  - III. Inbound Security Gate (HeadersInterceptor)
  - IV. Centralized Dependency Injection (container.py)
  - V. LLM Agnostic & Fallback Reliability
  - VI. Test-Driven Quality Gate & Zero Regressions
- Governance & Reference: Integrated with .agents/RULES.md and .agents/ARCHITECTURE.md
-->

# ai-reasoning-service Constitution

## Core Principles

### I. The Core Architecture: Use Cases vs. Context Services (NON-NEGOTIABLE)
- **Use Cases (`src/application/use_cases/`)**: Must remain thin, high-level orchestrators (~50–100 lines). They validate basic input arguments and coordinate domain services in a clear, sequential pipeline. They MUST NOT contain complex business algorithms, data transformations, string/entity parsing, or prompt manipulation.
- **Context Services (`src/application/services/<context>/`)**: Every complex algorithm, database integration, or domain strategy must be encapsulated into dedicated single-responsibility classes organized strictly by bounded context subdirectories (e.g., `services/alignment/`, `services/gene_interaction/`).
- **Single Responsibility Principle (SRP)**: One class = one capability. Services must be isolated, deterministic, and easily unit-tested.

### II. Ports & Adapters Isolation (Hexagonal Architecture)
- **REST Delivery / Controllers (`src/infrastructure/delivery/rest/controllers/`)**: Controllers must only deserialize request DTOs, invoke the Use Case orchestrator, and return response DTOs. Zero business logic is allowed in controllers.
- **Driven Adapters (`src/infrastructure/adapters/`)**: Adapters handle external communication (HTTP clients, PubTator, PubMed, database APIs, LLM providers). Domain and application layers MUST NOT depend directly on external protocols or libraries.
- **Domain Independence (`src/domain/`)**: Pure domain models and port interfaces with zero dependencies on frameworks, databases, or transport layers.

### III. Inbound Security Gate (`HeadersInterceptor`)
- **Mandatory Header Validation**: All protected endpoints MUST validate the incoming `x-user-id` header via `HeadersInterceptor`.
- **No Redundant Manual Checks**: Route controllers MUST NOT duplicate manual header presence checks (`if not x_user_id: raise HTTPException(400)`). The interceptor rejects unauthorized or malformed requests before they reach the controller.
- **Public Routes Exemption**: Only public routes (`/ai-reasoning/health`, `/`, `/ai-reasoning/docs`, `/ai-reasoning/openapi.json`, and CORS `OPTIONS` preflights) are exempted from header validation.

### IV. Centralized Dependency Injection (`container.py`)
- **Single Composition Root**: All ports, adapters, context services, and use cases are wired together in `src/infrastructure/container.py`.
- **Constructor Injection**: Use Cases and Services receive their dependencies through `__init__`, enabling trivial mocking during automated testing. No global state or hidden service lookups inside domain code.

### V. LLM Agnostic & Fallback Reliability
- **Port Abstraction**: All LLM interactions must implement `LLMReasoningPort` and be instantiated via the provider factory.
- **Provider Decoupling**: Support multiple LLM backends (Gemini, DeepSeek, NVIDIA, Ollama) via configuration without touching business logic.
- **Graceful Fallbacks**: When LLM calls fail, time out, or produce malformed JSON, services must degrade gracefully (e.g., returning deterministic heuristic/database results) and never crash the application or return unhandled 500 errors.

### VI. Test-Driven Quality Gate & Zero Regressions
- **100% Pass Rate Required**: Every pull request and feature implementation must maintain 100% test pass rate across unit and integration suites.
- **TDD Coverage**: Context services require isolated unit tests with mock adapters. Controllers require integration tests validating status codes, DTO schemas, and header interception.
- **CI/CD Compliance**: Changes must pass the automated GitHub workflow checks (CodeQL security analysis, Apache 2.0 license headers, and pytest).

## Technology Stack & Constraints

- **Language & Runtime**: Python 3.10+
- **Framework**: FastAPI with Pydantic v2 schemas
- **Testing**: `pytest` and `pytest-asyncio`
- **Containerization**: Docker multi-stage builds, non-root user execution, Jenkins CI/CD deployment
- **Default Port**: Container port 8000 mapped to host port 8009

## Development Workflow & Spec-Driven Gates

1. **Specification First**: Features and use cases begin with a `spec.md` defining requirements, user stories, and acceptance criteria.
2. **Technical Plan (`plan.md`)**: Architectural blueprint verified against this Constitution and `.agents/RULES.md`.
3. **Task Breakdown (`tasks.md`)**: Granular, testable tasks following TDD (tests first, then context services, then use case orchestrator, then controller).
4. **Execution & Verification**: Autonomous agents execute tasks and verify against acceptance criteria with zero regressions.

## Governance

This Constitution supersedes ad-hoc instructions. All PRs, code reviews, and AI agent outputs must strictly comply with:
- **Mandatory Development Rules**: [RULES.md](../../.agents/RULES.md)
- **Architecture Blueprints**: [ARCHITECTURE.md](../../.agents/ARCHITECTURE.md)
- **Use Case Specifications**: [.agents/use_cases/](../../.agents/use_cases/)

Amendments to this Constitution require explicit documentation, impact assessment, and review.

**Version**: 1.0.0 | **Ratified**: 2026-10-14 | **Last Amended**: 2026-10-14
