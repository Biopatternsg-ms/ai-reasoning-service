# Architecture & Development Rules for AI Agents and Developers

This document defines the **mandatory and non-negotiable rules** for developing, extending, and maintaining `ai-reasoning-service`. Any AI coding agent or software engineer contributing to this repository **must** read and adhere to these principles.

---

## 1. The Core Architecture Rule: Use Cases vs. Services

```
┌────────────────────────────────────────────────────────────────────────┐
│                          APPLICATION LAYER                             │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │ USE CASES (src/application/use_cases/)                         │   │
│   │                                                                │   │
│   │  • Pure High-Level Orchestrators (~50–100 LOC).                │   │
│   │  • Validate inputs (e.g., pipelineId, userId).                 │   │
│   │  • Call Services in a readable, sequential pipeline.           │   │
│   │  • ZERO complex business algorithms or parsing logic.          │   │
│   └───────────────────────────────┬────────────────────────────────┘   │
│                                   │ coordinates                        │
│                                   ▼                                    │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │ SERVICES (src/application/services/<context>/)                 │   │
│   │                                                                │   │
│   │  • Encapsulate all complex domain logic.                       │   │
│   │  • Organized strictly by bounded context subdirectories.       │   │
│   │  • Single Responsibility Principle (SRP): 1 class = 1 job.     │   │
│   │  • Isolated, deterministic, and easily unit-tested.            │   │
│   └────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

### ✅ DO:
- **Keep Use Cases thin**: A use case's `execute(...)` method should read like an executive summary or recipe of the business process.
- **Group Services by Context**: Whenever a use case needs business logic, create a dedicated subdirectory under `src/application/services/<context>/` (e.g., `services/alignment/`, `services/gene_interaction/`).
- **One Responsibility per Service**: E.g., `DirectMatchingService` only does Stage 1 exact matching; `LiteratureEvidenceService` only collects PubMed evidence.
- **Inject Services via Constructor**: Use Cases must receive their services in `__init__`, enabling trivial mocking during unit tests.

### ❌ DO NOT:
- **Never put complex logic in a Use Case**: No string manipulation algorithms, no LLM prompt generation, no database queries, no multi-stage branching logic directly inside `use_case_impl.py`.
- **Never create flat, unstructured services**: Do not dump arbitrary service files in `src/application/services/` without a context folder.
- **Never put business logic in Controllers**: FastApi route handlers in `src/infrastructure/delivery/rest/controllers/` must only deserialize request DTOs, invoke the Use Case, and return response DTOs.
- **Never put business logic in Ports or Adapters**: Driven adapters in `src/infrastructure/adapters/` only handle I/O and protocol translation (HTTP, LLM client APIs).

---

## 2. Inbound Security Rule (`HeadersInterceptor`)

- **Mandatory Header**: All secured routes **must** validate the incoming `x-user-id` header via [`HeadersInterceptor`](../src/infrastructure/config/interceptors/headers_interceptor.py).
- **No Manual Controller Checks**: Controllers must **not** duplicate manual `if not x_user_id: raise HTTPException(400)` checks. The interceptor rejects invalid requests before reaching the controller.
- **Context Access**: Endpoints and use cases receive the validated user ID via `request.state.user_id` or FastAPI `Header(..., alias="x-user-id")`.
- **Public Routes Exemption**: Only public routes (`/ai-reasoning/health`, `/`, `/ai-reasoning/docs`, `/ai-reasoning/openapi.json`, and CORS `OPTIONS` preflights) are exempted from header validation.

---

## 3. Dependency Injection Rule (`src/infrastructure/container.py`)

- **Single Composition Root**: All ports, adapters, context services, and use cases are wired together in [`src/infrastructure/container.py`](../src/infrastructure/container.py).
- **Instantiation Flow**:
  1. Instantiate driven adapters / ports (e.g., `PubMedHttpAdapter`, `BiologicalObjectsHttpAdapter`, `LLMAdapterFactory`).
  2. Instantiate context services, passing required ports.
  3. Instantiate use cases, passing the instantiated context services and ports.
  4. Expose clean getter methods (e.g., `container.get_alignment_use_case()`).

---

## 4. Multi-Provider LLM Integration Rule

- **Decoupled LLM Calls**: Never instantiate OpenAI, Gemini, or Ollama clients directly inside application logic.
- **Use `LLMReasoningPort`**: All LLM queries must pass through `LLMReasoningPort.generate_json(...)`.
- **Factory Pattern**: New LLM providers must be implemented in `src/infrastructure/adapters/llm/` and wired into `LLMAdapterFactory`.
- **Safe Fallbacks**: Every AI resolution service must implement safe fallback behavior (e.g., `AlignmentStatus.UNRESOLVED`) if an LLM call fails or times out.

---

## 5. Testing & Quality Gate Rules

Every pull request or code change must pass the test suite with **zero regressions**:

1. **Unit Test Services Individually**: Every service under `src/application/services/<context>/` must have a dedicated test file under `tests/unit/application/services/<context>/test_<service_name>.py`.
2. **Unit Test Use Cases as Orchestrators**: Test that the use case coordinates its services and handles validations properly under `tests/unit/application/`.
3. **Integration Test Delivery & Interceptor**: Test full HTTP request/response flows and header validations under `tests/integration/infrastructure/`.
4. **Run Before Committing**:
   ```bash
   PYTHONPATH=. pytest tests/ -v
   ```
   All tests must pass (16/16).
5. **License Headers**: All Python files must preserve or include the Apache 2.0 license header configured in `.github/license-template.tmpl`.

---

## 6. Use Case Documentation Rule (`.agents/use_cases/`)

Living documentation is mandatory and must always stay synchronized with the codebase:

- **Modifying an Existing Use Case**: Whenever a use case is altered (contract changes, new pipeline steps, modified input/output DTOs, or changed business rules), the corresponding documentation file in `.agents/use_cases/<USE_CASE_NAME>.md` **MUST be updated immediately** in the same pull request or commit.
- **Creating a New Use Case**: When creating a new use case, a comprehensive specification file **MUST be created** at `.agents/use_cases/<USE_CASE_NAME>.md` detailing:
  1. Business objective and context.
  2. Input / Output contracts (DTOs) and endpoints.
  3. Step-by-step pipeline execution flow (orchestrator vs. context services).
  4. Error handling and LLM fallback behaviors.
  5. The new use case must also be registered in the Use Cases table in `.agents/README.md`.
- **Zero Drift**: Code and documentation must never drift apart. An implementation without up-to-date documentation in `.agents/use_cases/` is considered incomplete.

---

## 7. Checklist: Creating or Modifying a Use Case

Follow this exact sequence when adding or updating a capability:

- [ ] **Step 1**: Create or update `src/application/services/<context>/`.
- [ ] **Step 2**: Implement granular, single-responsibility service classes inside that folder and export them in `__init__.py`.
- [ ] **Step 3**: Define or update the abstract use case port in `src/application/use_cases/<use_case_name>_use_case.py`.
- [ ] **Step 4**: Implement the thin orchestrator in `src/application/use_cases/impl/<use_case_name>_use_case_impl.py` (receives services in `__init__`, calls them sequentially in `execute`).
- [ ] **Step 5**: Wire ports, services, and the use case in `src/infrastructure/container.py`.
- [ ] **Step 6**: Create or update the REST controller and DTOs in `src/infrastructure/delivery/rest/` and register the router in `src/main.py`.
- [ ] **Step 7**: Write unit tests for the services and integration tests for the controller (all 16+ tests must pass).
- [ ] **Step 8 (MANDATORY)**: Create or update documentation in `.agents/use_cases/<USE_CASE_NAME>.md` and keep `.agents/README.md` in sync.

