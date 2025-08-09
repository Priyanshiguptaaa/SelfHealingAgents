# Self-Healing E-commerce Agents

An autonomous reactive agent system that detects, diagnoses, and auto-fixes e-commerce issues in real-time.

## Architecture Overview

### Core Components
- **Sensor Ingestors**: Catalog Delta, API Probes, Runtime Validators
- **Event Bus**: Redis Streams for real-time event processing
- **RCA Agent**: Root Cause Analysis with pattern matching
- **Patch Generator**: Code fix generation using Morph Apply API
- **Guardrails**: Safety policies and validation
- **Verifier**: Replay and smoke testing
- **Real-time UI**: Live trace visualization with SSE

### Use Case: Return Policy Sync Failure
1. Nightly catalog update changes return policies
2. Sync code misses `return_policy` field → DB has nulls
3. Customer tries to return → `CheckReturnEligibility` fails schema validation
4. Validator detects `SchemaMismatch(return_policy missing)`
5. RCA Agent analyzes trace + catalog delta → identifies sync bug
6. Patch Generator creates fix using Morph Apply API
7. Guardrails approve → hot reload → verify → heal complete
8. UI shows live progress: ❌ → ✅ "Healed in 6.8s"

## Tech Stack
- **Frontend**: React + TypeScript + Vite + TailwindCSS
- **Backend**: FastAPI + Python + Redis + PostgreSQL
- **AI**: Morph Apply API for code generation
- **Real-time**: Server-Sent Events (SSE)

## Quick Start

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Services
```bash
# Redis (for event bus)
docker run -p 6379:6379 redis:alpine

# PostgreSQL (for trace store)
docker run -p 5432:5432 -e POSTGRES_DB=selfheal -e POSTGRES_PASSWORD=password postgres:13
```

## Live Demo Flow
1. Navigate to http://localhost:5173
2. Trigger a schema validation failure
3. Watch the real-time healing process
4. See the code diff and verification results

## Key Features
- **Autonomous Detection**: No human intervention required
- **Real-time Healing**: Sub-10 second fix cycles
- **Safe Patching**: Guardrails + rollback on failure
- **Live Visualization**: See every step as it happens
- **Audit Trail**: Complete history of all healing actions