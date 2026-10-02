# ai-reasoning-service

Biomedical entity alignment, disambiguation, and AI reasoning microservice for the **BioPatternsG** platform, built using **Hexagonal Architecture (Ports and Adapters / DDD)**.

---

## 1. Architecture Overview

The microservice strictly adheres to Hexagonal Architecture divided into three main layers:

```text
src/
├── domain/                          # 🟢 Pure Business Core (Zero external dependencies)
│   ├── models/                      # Domain entities (AlignedItem, AlignmentProposal, PreAlignment)
│   ├── ports/                       # Outbound Driven Ports (PubMedDataPort, LLMReasoningPort)
│   └── exceptions/                  # Domain exceptions (DomainException, AlignmentException)
│
├── application/                     # 🟡 Application Layer (Use Cases & Heuristics)
│   ├── use_cases/                   # Inbound Driving Ports (GenerateAlignmentProposalUseCase)
│   │   └── impl/                    # Concrete Use Case implementations
│   └── prompts/                     # Biomedical micro-prompts & system instructions
│
└── infrastructure/                  # 🔴 Infrastructure Layer (Technical Adapters & Delivery)
    ├── config/                      # Pydantic Settings (.env)
    ├── container.py                 # Dependency Injection Container (Wiring)
    ├── delivery/rest/               # Driving Inbound HTTP Adapters (FastAPI Routers & DTOs)
    └── adapters/                    # Driven Outbound Adapters (PubMedHttpAdapter, GeminiAdapter, OllamaAdapter)
```

---

## 2. Features

* **Hexagonal / Clean Architecture**: Total decoupling between biological domain logic, frameworks, and external APIs.
* **AI-Assisted Entity Alignment**: Resolves unaligned entities (`noAligned`) and disambiguates candidate alternatives (`alignedAs`).
* **Hybrid LLM Support (Provider-Agnostic)**:
  * **Cloud Mode (Active)**: Powered by **Google Gemini (1.5 Flash)** for ultra-fast, high-context inferences without requiring local GPUs.
  * **Local Mode (Extensible)**: Built-in support for **Ollama** (`gemma2:9b`, `biomistral:7b`).
* **Decoupled from Database**: Consumes biological knowledge directly via the `pubmed-integration` API (Quarkus).
* **Designed for Human-in-the-Loop**: Produces structured proposals for user review, edition, and approval in `biopatternsg-ui`.

---

## 3. Main Endpoints

All endpoints use the `/ai-reasoning/...` prefix (without `/api` prefix for seamless API Gateway compatibility):

| Method | Endpoint | Required Headers | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/ai-reasoning/alignments/v1/proposal/{pipelineId}` | `x-user-id` | Generates the alignment proposal for a pipeline, forwarding user ID to `pubmed-integration`. |
| `GET` | `/ai-reasoning/health` | None | Returns service health status and active provider configuration. |
| `GET` | `/ai-reasoning/docs` | None | Interactive Swagger / OpenAPI documentation. |

### Sample Response (`proposal/{pipelineId}`):
```json
{
  "pipelineId": "125789-aqserv",
  "objects": [
    {
      "current": "SST",
      "aligned": "SST",
      "status": "DIRECT_MATCH",
      "reason": "Direct match in PubTator synonyms"
    },
    {
      "current": "TATA",
      "aligned": "TBP",
      "status": "RESOLVED_BY_AI",
      "reason": "TATA-binding protein encoded by TBP gene [Criterion: canonical_gene_mapping]"
    },
    {
      "current": "LANREOTIDE",
      "aligned": "OCTREOTIDE",
      "status": "RESOLVED_BY_AI",
      "reason": "Somatostatin synthetic analog equivalence [Criterion: functional_analog]"
    }
  ]
}
```

---

## 4. Configuration & Environment Variables

Copy `.env.example` to `.env` and set your configuration variables:

```bash
cp .env.example .env
```

| Variable | Description | Default Value |
| :--- | :--- | :--- |
| `PUBMED_INTEGRATION_URL` | Base URL of the `pubmed-integration` microservice | `http://pubmed-integration:8080` |
| `LLM_PROVIDER` | Active LLM provider (`gemini` or `ollama`) | `gemini` |
| `GEMINI_API_KEY` | Google AI Studio API key | *(Required when provider=gemini)* |
| `LLM_MODEL_NAME` | Gemini model to use | `gemini-1.5-flash` |
| `OLLAMA_API_URL` | Local Ollama URL (when provider=ollama) | `http://localhost:11434` |
| `APP_PORT` | Application listening port | `8000` |

---

## 5. Running with Docker

### Build the Docker image:
```bash
docker build -t biopatternsg/ai-reasoning-service:latest .
```

### Run the container:
```bash
docker run -d \
  --name ai-reasoning-service \
  -p 8000:8000 \
  -e GEMINI_API_KEY="your_gemini_api_key_here" \
  -e PUBMED_INTEGRATION_URL="http://host.docker.internal:8080" \
  biopatternsg/ai-reasoning-service:latest
```

---

## 6. Local Development & Testing

```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run unit and integration tests
pytest tests/ -v

# Run the server with hot-reload (limiting watch to src directory)
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir src
```
