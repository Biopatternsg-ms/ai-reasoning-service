# ai-reasoning-service

Biomedical entity alignment, disambiguation, and AI reasoning microservice for the **BioPatternsG** platform.

---

## 1. Features

* **AI-Assisted Entity Alignment**: Resolves unaligned entities (`noAligned`) and disambiguates candidate alternatives (`alignedAs`).
* **Hybrid LLM Support (Provider-Agnostic)**:
  * **Cloud Mode (Active)**: Powered by **Google Gemini (1.5 Flash)** for ultra-fast, high-context inferences without requiring local GPUs.
  * **Local Mode (Extensible)**: Built-in support for **Ollama** (`gemma2:9b`, `biomistral:7b`).
* **Decoupled from Database**: Consumes biological knowledge directly via the `pubmed-integration` API (Quarkus).
* **Designed for Human-in-the-Loop**: Produces structured proposals for user review, edition, and approval in `biopatternsg-ui`.

---

## 2. Main Endpoints

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

## 3. Configuration & Environment Variables

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

## 4. Running with Docker

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

## 5. Local Development Setup

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the server with hot-reload
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```
