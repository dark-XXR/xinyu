# High-EQ Love Reply Assistant

Contract-first monorepo for the Android client, admin web application, HTTP API,
AI worker, and asynchronous jobs.

## Repository layout

- `apps/android`: Kotlin/Jetpack Compose Android client.
- `apps/admin-web`: React/TypeScript administration application.
- `services/api`: FastAPI user and administration API.
- `services/ai-worker`: OCR, model orchestration, and safety processing.
- `services/async-worker`: exports, share cards, reconciliation, and other jobs.
- `contracts`: OpenAPI, events, webhooks, and shared examples.
- `database`: append-only migrations and development seed data.
- `packages`: generated clients, contract fixtures, and shared observability code.

## Local API

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn love_reply_api.main:app --reload
```

The health endpoint is available at `http://127.0.0.1:8000/health`.

## Infrastructure

Copy `.env.example` to `.env`, then run `docker compose up -d postgres redis minio`.
Development credentials are local-only and must never be reused outside this
workspace.

