# ClaimBlitz — Enterprise Multi-Agent Medical Insurance Claim Processor

> **9 specialized AI agents** collaborate in real-time to process medical insurance claims — extracting data, validating codes, detecting fraud, assessing risk, debating disagreements, and delivering explainable approve/reject decisions in under 30 seconds.

---

## Table of Contents

- [Overview](#overview)
- [Live Demo Flow](#live-demo-flow)
- [System Architecture](#system-architecture)
- [The 9 AI Agents — Detailed](#the-9-ai-agents--detailed)
- [Multi-Agent Communication Protocol](#multi-agent-communication-protocol)
- [Debate Mode & Consensus](#debate-mode--consensus)
- [Technology Stack — Complete](#technology-stack--complete)
- [Installation & Setup](#installation--setup)
- [API Documentation](#api-documentation)
- [Frontend Features](#frontend-features)
- [Agent Pipeline — Step by Step](#agent-pipeline--step-by-step)
- [Security & Compliance](#security--compliance)
- [Observability & Monitoring](#observability--monitoring)
- [Deployment](#deployment)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Configuration Reference](#configuration-reference)
- [Design Decisions](#design-decisions)

---

## Overview

ClaimBlitz replaces traditional sequential claim processing (which takes 30-90 days) with an autonomous multi-agent AI system that processes claims in seconds.

**What makes it different from a simple LLM call:**

| Feature | Simple LLM App | ClaimBlitz Multi-Agent |
|---------|---------------|----------------------|
| Architecture | One model, one prompt | 9 independent agents with own personas |
| Memory | Stateless | Per-agent Pinecone vector memory |
| Disagreement handling | None | Structured debate with voting |
| Explainability | "Here's my answer" | Evidence + confidence + reasoning per agent |
| Scalability | Single request | Celery workers, horizontal scaling |
| Fault tolerance | Crash = fail | Agent errors isolated, pipeline continues |
| Human oversight | None | Auto-escalation below 80% confidence |

---

## Live Demo Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  User uploads claim_form.pdf via frontend                       │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  POST /process → FastAPI receives file                           │
│  PyMuPDF extracts text from PDF                                  │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌───────────────────────────────────────────────────────────────────┐
│  SUPERVISOR ENGINE (State Machine)                                │
│                                                                   │
│  Stage 1: SCANNING                                                │
│    └─ Scanner Agent → "Is this a valid, processable document?"    │
│                                                                   │
│  Stage 2: OCR EXTRACTION                                          │
│    └─ OCR Agent → Extract patient, diagnosis, codes, amounts      │
│                                                                   │
│  Stage 3: VALIDATION                                              │
│    └─ Validator Agent → Check formats, dates, code syntax         │
│                                                                   │
│  Stage 4: PARALLEL ANALYSIS (all 4 run independently)             │
│    ├─ Medical Expert → "Is ICD code clinically plausible?"        │
│    ├─ Policy Expert → "Is this covered? Pre-auth needed?"         │
│    ├─ Fraud Detection → "Duplicate? Upcoding? Pattern match?"     │
│    └─ Risk Assessment → "Risk score: 0.15 (LOW)"                  │
│                                                                   │
│  Stage 5: CONSENSUS CHECK                                         │
│    ├─ All agree? → APPROVE/REJECT                                 │
│    └─ Disagree? → DEBATE MODE (voting rounds)                     │
│         └─ Still unresolved? → JUDGE AGENT rules                  │
│              └─ Confidence < 80%? → HUMAN ESCALATION              │
│                                                                   │
│  Stage 6: COMMUNICATION                                           │
│    └─ Communication Agent → Draft email + SMS for policyholder    │
└──────────────────────────┬────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  JSON Response to Frontend                                       │
│  {claimData, riskScore, recommendation, email, findings[]}       │
└──────────────────────────────────────────────────────────────────┘
```

---

## System Architecture

```
                    ┌────────────────────────┐
                    │   React Frontend       │
                    │   (Vite + Tailwind)    │
                    └───────────┬────────────┘
                                │ POST /process
                                ▼
                    ┌────────────────────────┐
                    │   FastAPI Backend      │
                    │   (uvicorn, async)     │
                    └───────────┬────────────┘
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                   │
              ▼                 ▼                   ▼
   ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
   │  Groq LLM    │  │  MongoDB     │  │  Pinecone        │
   │  (reasoning) │  │  (persist)   │  │  (vector memory) │
   └──────────────┘  └──────────────┘  └──────────────────┘
              │
              ▼
   ┌───────────────────────────────────────────────────┐
   │          SUPERVISOR ORCHESTRATOR                  │
   │  ┌────┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐       │
   │  │Scan│→│OCR│→│Val│→│Med│ │Pol│ │Frd│ │Rsk│       │
   │  └────┘ └───┘ └───┘ │Exp│ │Exp│ │Det│ │Ass│       │
   │                       └─┬─┘ └─┬─┘ └─┬─┘ └─┬─┘     │
   │                         └──┬──┘   ┌──┘     │      │
   │                            ▼      ▼        ▼      │
   │                      ┌──────────────────┐         │
   │                      │  DEBATE / JUDGE  │         │
   │                      └────────┬─────────┘         │
   │                               ▼                   │
   │                      ┌──────────────┐             │
   │                      │ Communication│             │
   │                      └──────────────┘             │
   └───────────────────────────────────────────────────┘
```

---

## The 9 AI Agents — Detailed

### 1. Scanner Agent (`agentcore/agents/scanner.py`)
- **Input:** File metadata (filename, size, page count)
- **Output:** `APPROVE` (proceed) or `REJECT` (unprocessable file)
- **LLM Prompt:** Assesses document type, quality, and processability
- **Memory:** Remembers scan patterns for future triage

### 2. OCR Agent (`agentcore/agents/ocr.py`)
- **Input:** Raw extracted text from PDF
- **Output:** Structured JSON with 13+ fields (patient, diagnosis, codes, amounts, dates)
- **LLM Prompt:** Field-by-field extraction with confidence per field
- **Special method:** `extract()` returns the full structured claim data

### 3. Validator Agent (`agentcore/agents/validator.py`)
- **Input:** Extracted claim data
- **Output:** List of issues (errors vs warnings), `APPROVE`/`FLAG`/`REJECT`
- **Checks:** Date formats, ICD-10 regex (`[A-Z]\d{2}(\.\d{1,4})?`), CPT 5-digit, positive amounts
- **Does NOT:** Assess clinical plausibility (that's Medical Expert's job)

### 4. Medical Expert Agent (`agentcore/agents/medical_expert.py`)
- **Input:** Claim data + vector memory of past cases
- **Output:** Clinical plausibility verdict with evidence
- **Checks:** ICD-code matches diagnosis text? Procedure appropriate? Amount reasonable?
- **Memory:** Recalls similar past diagnoses for pattern matching
- **Peer Q&A:** Other agents can ask it clinical questions via the message bus

### 5. Policy Expert Agent (`agentcore/agents/policy_expert.py`)
- **Input:** Claim data + coverage rules
- **Output:** Coverage determination with policy citations
- **Checks:** Pre-authorization required? Exclusions apply? In-network? Benefit limits?
- **Memory:** Recalls policy precedents
- **Peer Q&A:** Answers policy questions from other agents

### 6. Fraud Detection Agent (`agentcore/agents/fraud_detection.py`)
- **Input:** Claim data + vector memory of known fraud patterns
- **Output:** Fraud score (0-1), indicators list, verdict
- **Checks:** Duplicate submissions, upcoding, unbundling, impossible combinations, amount anomalies
- **Memory:** **Heavy user** — searches for similar historical fraud patterns
- **Tags:** Each indicator has type + severity (high/medium/low)

### 7. Risk Assessment Agent (`agentcore/agents/risk_assessment.py`)
- **Input:** Claim data
- **Output:** Numeric risk score (0-1), risk label (LOW/MEDIUM/HIGH/CRITICAL), risk factors
- **Factors:** Amount vs service type, procedure complexity, provider history, demographics

### 8. Communication Agent (`agentcore/agents/communication.py`)
- **Input:** Final decision + reasoning + claim data
- **Output:** Email draft, SMS draft, internal processing note
- **Special method:** `draft()` returns all communication templates
- **Tone:** Professional, empathetic, clear

### 9. Judge Agent (`agentcore/agents/judge.py`)
- **Input:** All analyst findings + debate history
- **Output:** Binding `JudgeRuling` with verdict, confidence, dissenting agents list
- **Principles:** Fraud signals weigh heavily, medical plausibility > policy technicalities
- **Special method:** `rule()` returns a `JudgeRuling` object
- **Escalation:** If own confidence < 80%, flags for human review

---

## Multi-Agent Communication Protocol

Agents communicate via typed `AgentMessage` envelopes on a message bus:

```python
class AgentMessage:
    message_id: str          # Unique ID
    type: MessageType        # REQUEST, RESPONSE, QUESTION, ANSWER, OBJECTION, VOTE, etc.
    sender: AgentRole        # Who sent this
    recipient: AgentRole     # Who it's for (None = broadcast)
    claim_id: str            # Which claim this is about
    correlation_id: str      # Ties request to response
    causation_id: str        # What message caused this one
    trace_id: str            # End-to-end tracing
    payload: dict            # The actual content
```

**Message Types (11):**
| Type | Purpose |
|------|---------|
| `REQUEST` | Ask an agent to do work |
| `RESPONSE` | Result of a request |
| `QUESTION` | Ask a peer for information |
| `ANSWER` | Reply to a question |
| `ASSERTION` | Publish a finding |
| `OBJECTION` | Challenge another agent's finding |
| `VOTE` | Cast a vote in debate |
| `ESCALATION` | Hand off to human |
| `ERROR` | Agent failed |
| `EVENT` | Lifecycle notification |
| `HEARTBEAT` | Liveness signal |

---

## Debate Mode & Consensus

When analysts disagree (e.g., Medical Expert says APPROVE but Fraud Detection says REJECT):

1. **Detection:** Supervisor finds mixed verdicts or any confidence < 80%
2. **Debate Round 1:** All 4 analysts cast a `Vote` (approve/reject/escalate) with justification
3. **Super-majority check:** If 3/4 agree → consensus reached
4. **Debate Round 2:** If not, another round with awareness of prior votes
5. **Judge Rules:** After 2 rounds without consensus, the Judge Agent weighs all evidence
6. **Escalation:** If Judge's confidence < 80% → `HUMAN_ESCALATION` with full decision trail

```python
class JudgeRuling:
    claim_id: str
    verdict: Verdict                    # approve/reject/flag
    confidence: ConfidenceScore         # 0.0-1.0 with rationale
    dissenting_agents: list[AgentRole]  # Who disagreed
    rationale: str                      # Full explanation
    decision_path: DecisionPath         # Complete audit trail
    requires_human_review: bool
```

---

## Technology Stack — Complete

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Frontend | React | 18+ | UI framework |
| Frontend Build | Vite | 5+ | Fast dev server + bundler |
| Frontend Styling | Tailwind CSS | 3+ | Utility-first CSS |
| Frontend Animation | Framer Motion | 10+ | Smooth transitions |
| Backend Framework | FastAPI | 0.116+ | Async REST API |
| LLM Provider | Groq | Free tier | Fast inference (llama-3.1-8b-instant) |
| LLM Protocol | OpenAI-compatible | v1 | Standard chat completions API |
| Vector Database | Pinecone | 9.1.0 SDK | Semantic agent memory |
| Document Database | MongoDB | Atlas / Local | Claim persistence |
| Cache / Pub-Sub | Redis | 6.4+ | Blackboard + real-time events |
| Task Queue | Celery | 5.6.3 | Distributed processing |
| Message Broker | RabbitMQ | 3.x | Celery broker + event bus |
| Embeddings | OpenAI text-embedding-3-small | 1536 dim | Text → vectors for memory |
| PDF Parsing | PyMuPDF (fitz) | 1.26+ | Extract text from claim PDFs |
| ORM (optional) | SQLAlchemy | 2.0 | Postgres support if needed |
| Migrations (optional) | Alembic | 1.18 | Schema migrations |
| Auth | PyJWT | HS256 | Bearer token verification |
| Rate Limiting | slowapi | — | Per-IP request throttling |
| Tracing | OpenTelemetry | 1.44+ | Distributed traces |
| Metrics | Prometheus | — | /metrics endpoint |
| Error Tracking | Sentry | — | Exception capture |
| Containerization | Docker | — | Reproducible builds |
| Orchestration | Kubernetes | — | Production deployment |

---

## Installation & Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- MongoDB (local or [MongoDB Atlas](https://www.mongodb.com/atlas) free tier)
- A Groq API key (free at https://console.groq.com)

### Step 1: Clone & Backend Setup

```bash
git clone <repo-url>
cd ClaimBlitz/backend

python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/Mac

pip install -r requirements.txt
```

### Step 2: Configure Environment

```bash
cp .env.example .env
```

Edit `backend/.env`:
```env
# REQUIRED — Get free key at https://console.groq.com
OPENAI_API_KEY=gsk_your_groq_api_key_here
OPENAI_MODEL=llama-3.1-8b-instant
OPENAI_BASE_URL=https://api.groq.com/openai/v1

# REQUIRED — MongoDB connection
MONGODB_URL=mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true
MONGODB_DB_NAME=claimblitz
```

### Step 3: Start Backend

```bash
uvicorn main:app --reload --port 8000
```

Verify: http://localhost:8000/docs (interactive API docs)

### Step 4: Frontend Setup

```bash
cd ../frontend
npm install
npm run dev
```

Open: http://localhost:5173

### Step 5: Test

Upload the included `backend/test_claim.pdf` through the frontend UI.

---

## API Documentation

### `POST /process` — Main Endpoint (Frontend uses this)

**Request:** `multipart/form-data` with a `file` field (PDF/image)

**Response:**
```json
{
  "claimData": {
    "patient_name": "Sarah Johnson",
    "diagnosis": "Type 2 Diabetes",
    "diagnosis_codes": ["E11.9"],
    "procedure_codes": ["99214"],
    "billed_amount": 275.0,
    "service_date": "2026-07-28",
    "provider_name": "Downtown Family Medicine"
  },
  "riskScore": 0.15,
  "riskLabel": "LOW",
  "recommendation": "APPROVE",
  "riskReasons": ["No fraud indicators detected", "Amount reasonable for service type"],
  "riskModel": {
    "engine": "multi-agent",
    "modelName": "claimblitz-9-agent-v2"
  },
  "email": "Subject: Claim Approved...",
  "whatsapp": "Claim Update: APPROVE | Risk: LOW",
  "findings": [
    {"agent": "scanner", "verdict": "approve", "confidence": 0.95, "reasoning": "Valid PDF..."},
    {"agent": "medical_expert", "verdict": "approve", "confidence": 0.88, "reasoning": "ICD E11.9 matches..."},
    {"agent": "fraud_detection", "verdict": "approve", "confidence": 0.92, "reasoning": "No fraud signals..."}
  ],
  "stage": "completed",
  "decisionSteps": 8
}
```

### Other Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Returns `{"status": "ok", "version": "2.0.0"}` |
| `GET` | `/health/agents` | Lists all 10 agent roles + system status |
| `POST` | `/v2/claims` | Async claim submission (returns immediately with claim_id) |
| `GET` | `/v2/claims/{id}` | Poll claim processing status |
| `GET` | `/v2/claims/{id}/workflow` | Full workflow: findings, debate rounds, ruling, decision path |
| `POST` | `/v2/claims/{id}/pause` | Pause a running claim |
| `POST` | `/v2/claims/{id}/resume` | Resume paused claim |
| `POST` | `/v2/claims/{id}/retry` | Retry a failed claim |
| `GET` | `/v2/escalations` | List all pending human escalations |
| `POST` | `/v2/escalations/{id}/resolve` | Resolve with notes + optional verdict override |

---

## Frontend Features

- **Landing Page:** Animated hero, problem/solution comparison, 3-phase explainer
- **Dashboard:** Real-time agent processing with progress animation
- **Agent Command Center:** Shows all 8 visible agent steps with status (idle/processing/completed)
- **Terminal Window:** Live logs showing agent-to-agent communication
- **Risk Meter:** Circular gauge with color-coded risk levels
- **Document Viewer:** CMS-1500 form simulation showing extracted data
- **Output Section:** 4 tabs — Email Draft, WhatsApp, Claim Summary, Agent Findings
- **Agent Findings Tab:** Color-coded cards per agent with verdict badges and confidence %
- **Demo Mode:** Built-in toggle for testing without file upload
- **Drag & Drop:** File upload via drag-and-drop or file picker
- **Responsive:** Works on desktop and tablet

---

## Agent Pipeline — Step by Step

### Phase 1: Document Intake (Sequential)

| Step | Agent | Duration | What Happens |
|------|-------|----------|--------------|
| 1 | Scanner | ~1.5s | Validates file format, estimates quality, determines document type |
| 2 | OCR | ~2s | Extracts 13+ structured fields with confidence scoring |
| 3 | Validator | ~1.5s | Checks date formats, code syntax, required fields present |

### Phase 2: Expert Analysis (Sequential with rate-limit delays)

| Step | Agent | Duration | What Happens |
|------|-------|----------|--------------|
| 4 | Medical Expert | ~2s | Assesses ICD/CPT consistency, clinical plausibility |
| 5 | Policy Expert | ~2s | Checks coverage, exclusions, pre-auth requirements |
| 6 | Fraud Detection | ~2s | Searches vector memory for similar fraud patterns |
| 7 | Risk Assessment | ~2s | Computes numeric risk score with factor breakdown |

### Phase 3: Decision & Communication

| Step | Agent | Duration | What Happens |
|------|-------|----------|--------------|
| 8 | Judge (if needed) | ~2s | Rules on disagreements with binding verdict |
| 9 | Communication | ~1.5s | Drafts policyholder email + SMS |

**Total processing time:** ~15-25 seconds (Groq free tier with rate limit delays)

---

## Security & Compliance

| Feature | Implementation |
|---------|---------------|
| API Authentication | JWT Bearer tokens (HS256) |
| Role-Based Access | `require_role("admin", "reviewer")` dependency |
| Rate Limiting | 60 req/min per IP (configurable) |
| PII Masking | SSN, email, phone patterns stripped from logs |
| Prompt Injection Protection | Regex detection of known injection patterns |
| Secret Management | Environment variables, never in code |
| Dev Mode Bypass | Auth disabled in `ENVIRONMENT=development` |
| CORS | Configured for frontend dev server |
| Audit Trail | Every agent action logged with timestamp |

---

## Observability & Monitoring

| Tool | What It Does | Config |
|------|-------------|--------|
| **Prometheus** | Request metrics at `/metrics` | `PROMETHEUS_ENABLED=true` |
| **OpenTelemetry** | Distributed traces per claim | `OTEL_EXPORTER_OTLP_ENDPOINT=http://...` |
| **Sentry** | Error tracking + alerting | `SENTRY_DSN=https://...` |
| **Terminal Logs** | Frontend real-time agent activity | Built-in |
| **Decision Path** | Full audit trail per claim | Stored in MongoDB |

---

## Deployment

### Local Development
```bash
# Backend
cd backend && uvicorn main:app --reload --port 8000

# Frontend
cd frontend && npm run dev
```

### Docker Compose (Full Stack)
```bash
docker compose up -d
# Starts: Postgres, Redis, RabbitMQ, Pinecone Local, API, Worker
```

### Kubernetes (Production)
```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets.yaml      # Fill with real values first
kubectl apply -f k8s/api-deployment.yaml
kubectl apply -f k8s/worker-deployment.yaml
```

**Scaling:**
- API: 2-10 replicas (CPU-based HPA at 70%)
- Workers: 3-20 replicas (CPU-based HPA at 60%)

---

## Project Structure

```
ClaimBlitz/
├── README.md                          # This file
├── ARCHITECTURE.md                    # Detailed system design doc
├── docker-compose.yml                 # Full dev stack
├── k8s/                               # Kubernetes manifests
│   ├── namespace.yaml
│   ├── secrets.yaml
│   ├── api-deployment.yaml
│   └── worker-deployment.yaml
├── backend/
│   ├── main.py                        # uvicorn entrypoint
│   ├── requirements.txt               # Python dependencies
│   ├── .env.example                   # Config template
│   ├── Dockerfile
│   ├── test_claim.pdf                 # Demo file for testing
│   ├── conftest.py                    # Pytest fixtures
│   ├── tests/                         # Test suite
│   ├── utils/                         # JSON cleaner, PDF parser
│   └── agentcore/                     # ★ THE MULTI-AGENT SYSTEM ★
│       ├── __init__.py
│       ├── protocol.py                # Wire format, all shared types
│       ├── settings.py                # Pydantic-settings config
│       ├── llm.py                     # Groq/OpenAI async client
│       ├── base.py                    # Abstract Agent base class
│       ├── supervisor.py              # Workflow state machine
│       ├── memory.py                  # AgentMemory interface
│       ├── pinecone_memory.py         # Pinecone vector implementation
│       ├── tools.py                   # Tool/ToolRegistry
│       ├── bus.py                     # InProcessMessageBus
│       ├── blackboard.py             # Redis shared working memory
│       ├── worker.py                  # Celery task definitions
│       ├── observability.py           # Prometheus + OTel + Sentry
│       ├── security.py                # JWT + RBAC + PII masking
│       ├── agents/                    # 9 concrete agent classes
│       │   ├── scanner.py
│       │   ├── ocr.py
│       │   ├── validator.py
│       │   ├── medical_expert.py
│       │   ├── policy_expert.py
│       │   ├── fraud_detection.py
│       │   ├── risk_assessment.py
│       │   ├── communication.py
│       │   └── judge.py
│       ├── api/                       # FastAPI layer
│       │   ├── app.py                 # App factory + CORS
│       │   ├── routes.py              # All endpoints
│       │   ├── schemas.py             # Request/response models
│       │   └── deps.py                # Dependency injection
│       └── db/                        # MongoDB layer
│           ├── engine.py              # Motor client factory
│           └── repos.py               # CRUD repositories
└── frontend/
    ├── package.json
    ├── index.html
    ├── vite.config.js
    └── src/
        ├── App.jsx                    # Router
        ├── pages/
        │   ├── LandingPage.jsx        # Marketing page
        │   ├── Dashboard.jsx          # Main processing UI
        │   ├── SubmissionPage.jsx     # Claim submission portal
        │   └── InsurerPortalPage.jsx  # Insurer view
        ├── components/
        │   ├── AgentStepper.jsx       # Agent progress cards
        │   ├── DocumentViewer.jsx     # CMS-1500 simulation
        │   ├── OutputSection.jsx      # Results + findings tabs
        │   ├── RiskMeter.jsx          # Circular risk gauge
        │   └── TerminalWindow.jsx     # Live log console
        └── hooks/
            └── useClaimAgent.js       # API integration hook
```

---

## Testing

```bash
cd backend
pytest -q              # 5 tests covering health, claims, escalations
```

**Manual Testing:**
1. Start backend: `uvicorn main:app --reload --port 8000`
2. Start frontend: `cd frontend && npm run dev`
3. Upload `backend/test_claim.pdf` in the UI
4. Watch 9 agents process it in real-time
5. Check "Agent Findings" tab for per-agent verdicts

**Test with curl:**
```bash
curl -X POST http://localhost:8000/process -F "file=@test_claim.pdf"
```

---

## Configuration Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | **Yes** | — | Groq API key |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | LLM model name |
| `OPENAI_BASE_URL` | No | `https://api.openai.com/v1` | API base (use `https://api.groq.com/openai/v1` for Groq) |
| `MONGODB_URL` | **Yes** | `mongodb://localhost:27017` | MongoDB connection string |
| `MONGODB_DB_NAME` | No | `claimblitz` | Database name |
| `LLM_TEMPERATURE` | No | `0.1` | LLM randomness (0-1) |
| `LLM_TIMEOUT_SECONDS` | No | `45` | Per-request timeout |
| `LLM_MAX_RETRIES` | No | `2` | Retries before failover |
| `USE_OLLAMA_ONLY` | No | `false` | Skip Groq, use local Ollama |
| `PINECONE_API_KEY` | No | — | For vector memory (optional) |
| `PINECONE_USE_LOCAL` | No | `false` | Use Pinecone Local emulator |
| `REDIS_URL` | No | `redis://localhost:6379/0` | Redis for blackboard |
| `RABBITMQ_URL` | No | `amqp://guest:guest@localhost:5672/` | Celery broker |
| `JWT_SECRET_KEY` | No | — | JWT signing secret |
| `RATE_LIMIT_PER_MINUTE` | No | `60` | API rate limit |
| `ENVIRONMENT` | No | `development` | `development`/`staging`/`production` |
| `SENTRY_DSN` | No | — | Sentry error tracking |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | No | — | OpenTelemetry collector |

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Groq over OpenAI** | Free tier, 10x faster inference, same API format |
| **MongoDB over Postgres** | Claims are nested JSON documents — no ORM mismatch |
| **Sequential analysts (not parallel)** | Groq free tier has 30 req/min limit; delays avoid 429s |
| **InProcessMessageBus (not RabbitMQ by default)** | Simpler for dev; RabbitMQ wired via Celery for production |
| **Supervisor calls agents directly (not via bus)** | Bus is for agent-to-agent peer communication, not orchestration |
| **Each agent has own memory namespace** | Privacy: fraud patterns don't leak to medical assessments |
| **Validator doesn't kill pipeline** | Its issues are noted but other agents still get to weigh in |
| **LOW risk = APPROVE override** | If risk assessment says LOW, recommendation should be APPROVE regardless of flag verdicts |
| **Judge only invoked on disagreement** | Most claims have consensus — no need to waste a LLM call |
| **1.5s delays between Groq calls** | Respects free-tier rate limits while keeping processing flowing |

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run tests: `cd backend && pytest -q`
5. Commit: `git commit -m "feat: description"`
6. Push: `git push origin feature/my-feature`
7. Open a Pull Request

---

## License

Built for DYP Hackathon 2026.

---

*Designed and implemented as a true multi-agent system — not a wrapper around one LLM call. Each agent reasons independently, maintains private memory, and can challenge its peers.*
