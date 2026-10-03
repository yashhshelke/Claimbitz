# ClaimBlitz Backend

Multi-agent medical insurance claim processing system built with FastAPI.

## Quick Start

```bash
# Setup
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your Groq API key and MongoDB URL

# Run
uvicorn main:app --reload --port 8000
```

## Architecture

The backend is organized around the `agentcore` package:

- `main.py` — FastAPI app entrypoint
- `agentcore/` — The multi-agent system
  - `protocol.py` — Shared types (AgentMessage, AgentFinding, enums)
  - `llm.py` — Async LLM client (Groq primary, Ollama fallback)
  - `base.py` — Abstract Agent base class
  - `supervisor.py` — Workflow orchestrator (state machine)
  - `agents/` — 9 concrete agent implementations
  - `api/` — FastAPI routes and schemas
  - `db/` — MongoDB repositories
  - `memory.py` / `pinecone_memory.py` — Agent semantic memory
  - `blackboard.py` — Redis shared working memory
  - `worker.py` — Celery distributed task processing
  - `security.py` — JWT, RBAC, rate limiting
  - `observability.py` — OpenTelemetry, Prometheus, Sentry

## API

The main endpoint for the frontend is `POST /process` which accepts a PDF file upload and returns the full multi-agent analysis result.

Full REST API available under `/v2/*` prefix. See `/docs` for interactive OpenAPI docs.

## Testing

```bash
pytest -q
```

## Deployment

```bash
# Docker
docker build -t claimblitz-api .
docker run -p 8000:8000 --env-file .env claimblitz-api

# Celery worker (optional, for async processing)
celery -A agentcore.worker worker --loglevel=info --pool=solo
```
