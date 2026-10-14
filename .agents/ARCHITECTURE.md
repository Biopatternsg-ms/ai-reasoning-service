# Architecture & Technical Context for AI Agents

This document provides a technical deep-dive into the internals of `ai-reasoning-service` for autonomous agents and engineers.

---

## 1. Domain-Driven Design (DDD) Layers

```
Layer: Delivery (src/infrastructure/delivery/rest)
  │   - FastAPI Controllers (alignment_controller.py, health_controller.py)
  │   - Interceptors / Middlewares (HeadersInterceptor)
  ▼
Layer: Application (src/application)
  │   - Use Case Orchestrator (alignment_use_case_impl.py)
  │   - Specialized Domain Services (src/application/services/alignment/)
  │       * DirectMatchingService
  │       * DatabaseMatchingService
  │       * LiteratureEvidenceService
  │       * AIResolutionService
  │   - Prompt Builders (alignment_prompt.py)
  ▼
Layer: Domain (src/domain)
  │   - Entities, Aggregates & Enums (AlignedItem, AlignmentProposal, AlignmentStatus)
  │   - Abstract Ports / Contracts (PubMedDataPort, BiologicalObjectsPort, LLMReasoningPort)
  │   - Domain Exceptions
  ▼
Layer: Infrastructure Adapters (src/infrastructure/adapters)
      - PubMedHttpAdapter (HTTP calls to pubmed-integration)
      - BiologicalObjectsHttpAdapter (HTTP calls to search-biological-objects)
      - GeminiAdapter, DeepSeekAdapter, NvidiaAdapter, OllamaAdapter
```

---

## 2. Inbound Request Interception Pattern

- **File**: [`src/infrastructure/config/interceptors/headers_interceptor.py`](file:///home/yacson/Proyectos/biopatternsg-ms/services/ai-reasoning-service/src/infrastructure/config/interceptors/headers_interceptor.py)
- **Role**: Validates that all non-exempt incoming HTTP requests carry the `x-user-id` header.
- **Exemptions**:
  - `GET /ai-reasoning/health`
  - `GET /`
  - `GET /ai-reasoning/docs`, `GET /ai-reasoning/openapi.json`
  - All `OPTIONS` preflight requests.
- **Context Attachment**: Sanitizes the header value and stores it in `request.state.user_id`.

---

## 3. Alignment Business Logic Breakdown

### Stage 1: Deterministic Direct Matching (`DirectMatchingService`)
- Entities in `pre_data.aligned` -> Resolved directly as `AlignmentStatus.DIRECT_MATCH`.
- Entities in `pre_data.aligned_as` with an exact, case-insensitive match against any element in `alternative_ids` -> Resolved directly as `AlignmentStatus.DIRECT_MATCH`.
- Entities without exact match proceed to Stage 2.

### Stage 2: Database Matching (`DatabaseMatchingService`)
- For each ambiguous entity, queries `BiologicalObjectsPort.search_by_synonym(synonym=expert_object_name, user_id=user_id)`.
- If the first object returned contains synonyms matching any candidate in `alternative_ids`:
  - Resolved as `AlignmentStatus.RESOLVED_BY_DATABASE`.
  - Reason includes HGNC and UniProt identifiers (e.g. `Selected from BiopatternsG database (HGNC: 10471, UniProt: Q01196)`).
- Entities not matched proceed to Stage 3.

### Stage 3: AI-Assisted Disambiguation (`LiteratureEvidenceService` + `AIResolutionService`)
- Unaligned terms and remaining ambiguous terms are resolved using the LLM.
- **Literature Context**:
  - Fetches knowledge base events via `PubMedDataPort.get_kb_events_by_term`.
  - Collects all unique PubMed IDs without truncation.
  - Fetches publication titles and abstracts via `PubMedDataPort.get_publications_by_pmids`.
- **Inference**:
  - Injected into `build_alignment_prompt`.
  - Model generates JSON output conforming to:
    ```json
    {
      "resolutions": [
        {
          "current": "TATA",
          "aligned": "TBP",
          "reason": "TATA-binding protein canonical mapping",
          "criterion": "canonical_gene_mapping",
          "pubmedIds": ["10523821"]
        }
      ]
    }
    ```
  - Mapped to `AlignmentStatus.RESOLVED_BY_AI` (or `AlignmentStatus.UNRESOLVED` fallback).

---

## 4. How to Extend This Service

### Architecture Rule: Orchestrator vs Domain Services
- **`use_cases/impl/<name>_use_case_impl.py`**: Must strictly be an **orchestrator** (~50-100 LOC). It validates input arguments and coordinates service calls. It does NOT implement calculations, direct regex parsing, or prompt assembly.
- **`services/<context>/<service_name>.py`**: Encapsulates specific domain algorithms, deterministic lookups, API transformations, or LLM interactions.

### Adding a New Use Case
1. **Create context directory**: `src/application/services/<new_context>/`.
2. **Implement services**: Create granular classes following SRP in that directory and export them in `__init__.py`.
3. **Define use case**:
   - Port: `src/application/use_cases/<new_use_case>_use_case.py`.
   - Implementation: `src/application/use_cases/impl/<new_use_case>_use_case_impl.py` (receives services in `__init__`, calls them in `execute`).
4. **Wire dependencies**: Instantiate services and use case in `src/infrastructure/container.py`.
5. **Create delivery layer**: Controller and DTOs under `src/infrastructure/delivery/rest/`.
6. **Register route**: In `src/main.py`.
7. **Document**: Add `agents/use_cases/<NEW_USE_CASE>.md`.

### Adding a New Service into an Existing Context
1. Create a new service file under `src/application/services/<context>/`.
2. Follow SRP: The class should only focus on its specific strategy.
3. Export the class in `src/application/services/<context>/__init__.py`.
4. Inject it into `Container` in `src/infrastructure/container.py`.
5. Call it within the use case orchestrator.
6. Add unit tests under `tests/unit/application/services/<context>/`.

### Adding a New LLM Provider
1. Implement `LLMReasoningPort` in `src/infrastructure/adapters/llm/<new_provider>_adapter.py`.
2. Register the adapter in `LLMAdapterFactory.create_adapter()`.
3. Add configuration settings in `src/infrastructure/config/settings.py`.
