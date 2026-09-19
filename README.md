# MarketLens AI

An MCP-native agentic analytics platform that investigates why an Indian e-commerce business hit or missed its sales targets — using executed SQL, ML forecasts, anomaly detection, and festival-calendar context, reasoned over by an evidence-backed LLM agent.

**Dataset scope:** Indian e-commerce retail data (Kaggle), **April 2018 – March 2019** — not a generic CSV upload tool.

**Owner:** Fawaz Firoz Waghoo (Raj)

## Overview

MarketLens AI answers executive questions like *"We missed the sales target by 12%. What factors contributed to the gap?"* by orchestrating:

- **Safe SQL** against a curated PostgreSQL schema
- **Variance engine** (target vs actual by category, region, month)
- **Forecasting** (XGBoost / Prophet) and **anomaly detection** (Isolation Forest)
- **RAG** over synthetic policy/SOP documents (BM25 + pgvector embeddings)
- **LangGraph agent** that plans, calls MCP tools, collects evidence IDs, and writes a grounded report
- **Groq LLM** for natural-language synthesis (deterministic fallback when no API key)

## Architecture

```
Raw CSVs → PostgreSQL (+ pgvector) → ML Pipeline → MCP Tools → LangGraph Agent → FastAPI → Next.js UI
                              ↓
                     Festival Calendar + Synthetic RAG Docs
```

### MCP servers (Phase 2)

Five standalone MCP 2.x servers using `MCPServer`:

| Server | Module | Tool |
|--------|--------|------|
| sql_query | `mcp_servers/sql_query/server.py` | Safe parameterized SQL templates |
| forecast | `mcp_servers/forecast/server.py` | Category demand forecasts |
| anomaly_check | `mcp_servers/anomaly_check/server.py` | Isolation Forest / z-score anomalies |
| variance | `mcp_servers/variance/server.py` | Target achievement engine |
| rag_search | `mcp_servers/rag_search/server.py` | Hybrid BM25 + embedding search |

Run example: `python mcp_servers/variance/server.py`

### Investigation agent (Phase 3)

LangGraph flow: **Planner → Tool Executor → Evidence Collector → Report Agent**

Every numeric claim in the report cites tool/query provenance IDs.

## Tech stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14, React, Tailwind, Recharts |
| API | FastAPI, JWT auth (single-tenant) |
| Database | PostgreSQL + pgvector |
| ML | scikit-learn, XGBoost, Prophet, statsmodels |
| Agent | LangGraph, LangChain Core |
| LLM | **Groq only** (`langchain-groq`) — no Gemini/OpenAI |
| MCP | `mcp` SDK, in-process tool handlers + standalone servers |

## Local development

```powershell
# 1. Copy env and set secrets
Copy-Item .env.example .env
# Edit: JWT_SECRET, ADMIN_USERNAME, ADMIN_PASSWORD, optional GROQ_API_KEY

# 2. Setup database + data
pip install -r requirements.txt
python scripts/setup_db.py
# Place Kaggle CSVs in data/raw/ (see data provenance below)
python scripts/etl/load_data.py
python -m backend.app.ml.pipeline
python -m backend.app.rag

# 3. Backend API
uvicorn backend.app.main:app --reload --port 8000

# 4. Frontend (separate terminal)
cd frontend
Copy-Item .env.example .env.local
# Set NEXT_PUBLIC_API_BASE=http://localhost:8000
npm install
npm run dev
```

Or run `scripts/start_local.ps1` for automated setup + tests.

**Login:** credentials from `.env` (`ADMIN_USERNAME` / `ADMIN_PASSWORD`).

### Docker (full stack)

```bash
docker compose up --build
```

- Postgres + pgvector: `:5432`
- Backend API: `:8000`
- Frontend: `:3000`

## Environment variables

See [`.env.example`](.env.example) (backend) and [`frontend/.env.example`](frontend/.env.example) (frontend).

**Backend (required):** `POSTGRES_*`, `JWT_SECRET`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `CORS_ALLOWED_ORIGINS` (production)

**Backend (optional):** `GROQ_API_KEY`, `GROQ_MODEL`, `ANOMALY_DETECTOR_FALLBACK`

**Frontend (required in production):** `NEXT_PUBLIC_API_BASE`

Never commit `.env` or real secret values.

## Deployment

**Frontend:** Vercel (root directory `frontend`)

**Backend:** Container host (Render, Railway, Fly.io, etc.) — **not** Vercel Serverless

**Database:** Managed PostgreSQL with pgvector — external dependency

See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for the full production checklist.

**Production frontend:** https://marketlens-ai-liard.vercel.app (requires `NEXT_PUBLIC_API_BASE` and a deployed backend)

## Data provenance

| Source | Type | Notes |
|--------|------|-------|
| `data/raw/*.csv` | Real (Kaggle) | **Not in git**; obtain from [benroshan/ecommerce-data](https://www.kaggle.com/datasets/benroshan/ecommerce-data) |
| `data/reference/festival_calendar.csv` | Reference | Curated India festival dates |
| `data/rag/*.md` | **Synthetic** | Policy/SOP docs for demo only |

Customer names are never shown in the UI.

## Known limitations

- **Single fiscal year** (2018-04-01 → 2019-03-31): no YoY forecasting claims
- **pgvector**: primary path when extension available; local Postgres without `vector` uses documented `json_fallback`
- **Isolation Forest**: default detector; z-score only if `ANOMALY_DETECTOR_FALLBACK=zscore`
- **LLM**: Groq when `GROQ_API_KEY` configured; otherwise labeled `deterministic_fallback`
- **Single-tenant auth**: one admin user from env
- **No multi-tenancy / MLflow** in v1

## Tests

```bash
pytest tests/ -v
cd frontend && npm test
cd frontend && npm run build
```

Coverage spans ETL, ML, MCP, agent, RAG/pgvector, auth, CORS, frontend API smoke, LLM provider, flagship investigation.

## License

Kaggle dataset: [benroshan/ecommerce-data](https://www.kaggle.com/datasets/benroshan/ecommerce-data). Verify license before redistributing customer-level fields.
