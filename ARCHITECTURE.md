# ClaimBlitz Multi-Agent Architecture

## Overview

ClaimBlitz is an enterprise-grade collaborative multi-agent system for medical insurance claim processing. It replaces a sequential 4-function pipeline with 10 independent, specialized AI agents that communicate via structured messages, debate disagreements, and produce explainable, auditable decisions.

## System Design

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI (v2 API)                       │
│  POST /v2/claims → Celery Task → Supervisor Pipeline     │
│  GET  /v2/claims/{id} ← Redis Blackboard (real-time)     │
└──────────────┬──────────────────────────┬────────────────┘
               │                          │
       ┌───────▼───────┐          ┌───────▼───────┐
       │  Celery Worker │          │ Redis Blackboard│
       │  (RabbitMQ)    │          │  (pub-sub)      │
       └───────┬────────┘          └─────────────────┘
               │
       ┌───────▼────────────────────────────────────────┐
       │              SUPERVISOR ENGINE                   │
       │  State Machine: INGESTED → ... → COMPLETED      │
       └──┬──┬──┬──┬──┬──┬──┬──┬──┬─────────────────────┘
          │  │  │  │  │  │  │  │  │
  ┌───────┘  │  │  │  │  │  │  │  └───────┐
  ▼          ▼  ▼  ▼  ▼  ▼  ▼  ▼          ▼
Scanner   OCR  Val  Med Pol Frd Risk Comm  Judge
  │                  │   │   │   │
  │                  └───┴───┴───┘ ← parallel, can debate
  │                        │
  │                 ┌──────▼──────┐
  │                 │ Pinecone    │ (vector memory per agent)
  │                 │ (semantic)  │
  │                 └─────────────┘
  │
  └──→ PostgreSQL (persistent claim records, audit log)
```

## Agent Roster (10 Roles)

| Role | Responsibility | Memory Usage |
|------|---------------|--------------|
| **Supervisor** | Workflow orchestrator, state machine | N/A (engine, not agent) |
| **Scanner** | Document intake/triage | Scan patterns |
| **OCR** | Structured field extraction | Extraction patterns |
| **Validator** | Format/consistency checks | Validation rules |
| **Medical Expert** | Clinical plausibility (ICD/CPT) | Past diagnoses |
| **Policy Expert** | Coverage rules, exclusions | Policy precedents |
| **Fraud Detection** | Duplicate/upcoding detection | Fraud patterns |
| **Risk Assessment** | Numeric risk scoring | Risk baselines |
| **Communication** | Outbound message drafting | Tone templates |
| **Judge** | Consensus ruling on disagreements | Past rulings |

## Workflow State Machine

```
INGESTED → SCANNING → OCR_EXTRACTION → VALIDATION
  → PARALLEL_ANALYSIS (4 analysts concurrently)
  → [consensus?] → COMMUNICATION → COMPLETED
  → [disagreement?] → DEBATE (max 2 rounds, voting)
  → [still unresolved?] → JUDGMENT (Judge rules)
  → [confidence < 80%?] → HUMAN_ESCALATION
  → [else] → COMMUNICATION → COMPLETED | REJECTED
```

## Communication Protocol

Agents communicate exclusively through typed `AgentMessage` envelopes:
- **REQUEST/RESPONSE** — orchestrator dispatches work
- **QUESTION/ANSWER** — peer-to-peer knowledge sharing
- **ASSERTION** — publish a finding
- **OBJECTION** — challenge a peer's finding (triggers debate)
- **VOTE** — cast a vote in a debate round
- **ESCALATION** — hand off to human reviewer

Every message carries `trace_id`, `correlation_id`, `causation_id` for full replay/audit.

## Explainability

Every agent output is an `AgentFinding` containing:
- `verdict` (approve/reject/flag/abstain)
- `confidence` (0.0-1.0, calibrated, with rationale)
- `reasoning` (human-readable explanation)
- `evidence[]` (source, field, snippet, citation, weight)
- `referenced_fields[]`
- `tags[]`

The `DecisionPath` is an ordered audit trail across all agents.

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| API | FastAPI 0.116+ | REST endpoints, OpenAPI docs |
| LLM | Gemini (primary) + Ollama (fallback) | Agent reasoning |
| Vector DB | Pinecone (serverless / Local emulator) | Semantic memory |
| Relational DB | PostgreSQL 15 + SQLAlchemy 2.0 + Alembic | Persistence |
| Cache/Blackboard | Redis 6.4+ | Working memory, pub-sub |
| Task Queue | Celery 5.6 + RabbitMQ | Distributed processing |
| Observability | OpenTelemetry + Prometheus + Sentry | Traces, metrics, errors |
| Auth | JWT (HS256) + RBAC | API security |
| Deployment | Docker Compose (dev) / Kubernetes (prod) | Orchestration |

## Local Development

```bash
# Start infrastructure
docker compose up -d

# Run migrations
alembic upgrade head

# Start API server
uvicorn agentcore.api.app:app --reload

# Start Celery worker
celery -A agentcore.worker worker --loglevel=info --pool=solo
```

## Production Deployment (Kubernetes)

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets.yaml   # fill with real values first
kubectl apply -f k8s/api-deployment.yaml
kubectl apply -f k8s/worker-deployment.yaml
```

The API deployment scales 2-10 replicas (CPU-based HPA). Workers scale 3-20.

## Security

- JWT bearer token auth on all /v2 endpoints (bypassed in dev)
- Role-based access control (admin, reviewer, viewer)
- Rate limiting (60 req/min default, configurable)
- PII masking in logs (SSN, email, phone patterns stripped)
- Prompt injection detection on LLM inputs
- Secrets via K8s Secrets / env vars (never in code/git)

## Key Design Decisions

1. **True multi-agent, not sequential pipeline** — agents have independent personas, private memory, and can challenge each other.
2. **FastAPI only** (no Django) — single framework, no duplicated auth/ORM.
3. **Pinecone as vector database** — one namespace per agent role for private semantic memory.
4. **Debate mode is first-class** — disagreement triggers structured voting and Judge ruling rather than silent majority-wins.
5. **Human-in-the-loop at 80% threshold** — any confidence below 0.80 automatically escalates.
6. **Legacy pipeline preserved** — `backend/app/` (deterministic) and `backend/agents/` (old LLM) left on disk untouched.
