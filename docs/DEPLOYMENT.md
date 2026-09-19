# Production Deployment

MarketLens AI is a **split deployment**: Next.js on Vercel, FastAPI + Postgres elsewhere.

## Why not Vercel for the backend?

The FastAPI backend is **not suitable for Vercel Serverless Functions**:

- Heavy Python stack: scikit-learn, XGBoost, Prophet, sentence-transformers
- Long-running LangGraph investigation agent with MCP tool execution
- Persistent PostgreSQL + pgvector connections
- Startup ETL/ML/RAG pipeline (minutes, not milliseconds)

Deploy the backend as a **container** (Docker) on Render, Railway, Fly.io, AWS ECS, or similar.

## Architecture (production)

```
Browser → Vercel (Next.js) → HTTPS → Backend API (Docker)
                                         ↓
                              Managed PostgreSQL + pgvector
                                         ↓
                              Groq API (LLM reports)
```

## 1. PostgreSQL (external dependency)

Provision **managed Postgres with the `vector` extension** (pgvector). Examples:

- Neon (enable pgvector)
- Supabase
- Render Postgres + extension bootstrap
- Self-hosted `pgvector/pgvector:pg16` (see `docker-compose.yml`)

Apply schema:

```bash
psql $DATABASE_URL -f sql/schema.sql
psql $DATABASE_URL -f sql/schema_extensions.sql
psql $DATABASE_URL -f sql/03_pgvector.sql
```

Load data (Kaggle CSVs are **not** in git — place under `data/raw/`):

```bash
python scripts/etl/load_data.py
python -m backend.app.ml.pipeline
python -m backend.app.rag
```

## 2. Backend (container host)

Build and run `Dockerfile.backend` with these **required** env vars:

| Variable | Purpose |
|----------|---------|
| `POSTGRES_HOST` | DB hostname (not `localhost` in prod) |
| `POSTGRES_PORT` | DB port |
| `POSTGRES_DB` | Database name |
| `POSTGRES_USER` | DB user |
| `POSTGRES_PASSWORD` | DB password |
| `JWT_SECRET` | JWT signing secret |
| `ADMIN_USERNAME` | Login username |
| `ADMIN_PASSWORD` | Login password |
| `CORS_ALLOWED_ORIGINS` | Comma-separated Vercel frontend URL(s) |
| `GROQ_API_KEY` | Groq API key (optional; enables LLM reports) |
| `GROQ_MODEL` | Groq model id (default: `openai/gpt-oss-20b`) |

Health check: `GET /health` → `{"status":"ok",...}`

## 3. Frontend (Vercel)

Root directory: `frontend`

| Variable | Purpose |
|----------|---------|
| `NEXT_PUBLIC_API_BASE` | Public HTTPS backend URL (no trailing slash) |

**Do not** set `NEXT_PUBLIC_DEV_USERNAME` / `NEXT_PUBLIC_DEV_PASSWORD` in production.

Set backend `CORS_ALLOWED_ORIGINS` to match the Vercel production URL.

## 4. Verification checklist

- [ ] `GET /health` returns 200
- [ ] Login works from Vercel URL (no CORS errors in browser console)
- [ ] Dashboard KPIs and variance load
- [ ] Investigation resolves natural-language months
- [ ] Reports show `report_provider: groq` when `GROQ_API_KEY` is set
- [ ] Evidence IDs present in investigation responses
- [ ] No `localhost` API calls in browser network tab
