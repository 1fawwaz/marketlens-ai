# MarketLens AI — Final Gap Audit Report

**Date:** 2026-09-18  
**Verdict:** Project complete for v1 with documented environment limits. Critical gaps from the audit (Isolation Forest, pgvector path, LLM abstraction, flagship month resolution, env-based auth, smoke tests) are addressed and verified by tests. Fallbacks are labeled and are not claimed as primary implementations.

---

## Test suite (actual)

```text
pytest tests/ -v
============ 67 passed, 1 skipped, 2 warnings in 239.32s ============
```

| Suite | Result |
|-------|--------|
| Full `pytest tests/ -v` | **67 passed, 1 skipped** |
| Frontend `npm run build` | **PASS** |
| Isolation Forest injection | **4 hits / 13 injected** (`detector: isolation_forest`) |
| pgvector Docker (`:5433`) | **PASS** (`retrieval_backend: pgvector`) — covered in suite |
| Flagship 12% investigation | **mode=`percent_match`, month=`2019-02-01`** (not July 2018) |
| Explicit month investigation | **mode=`explicit_date`, month=`2018-11-01`** |
| Auto worst-month mode | **mode=`auto_worst_month`, month=`2018-07-01`** only when question requests auto/worst |

**1 skipped:** local `pgvector` schema assertion when host Postgres lacks the `vector` extension (expected ENVIRONMENT-LIMITED).

---

## Feature status (evidence-based)

| Feature | Classification | Evidence |
|---------|----------------|----------|
| Phase 0 ETL + schema + festival calendar | **IMPLEMENTED + VERIFIED** | Phase 0 tests; 500 orders / 1500 lines / 36 targets |
| Forecast models (naive / Prophet / XGBoost) | **IMPLEMENTED + VERIFIED** | Eval rows in DB; 7d & 30d MAE/MAPE recorded |
| 90-day forecast | **IMPLEMENTED + ENVIRONMENT-LIMITED** | Marked experimental; limited history → weak/empty 90d eval |
| Isolation Forest anomaly detection | **IMPLEMENTED + VERIFIED** | Real sklearn IF; injection **4/13**; z-score only if `ANOMALY_DETECTOR_FALLBACK=zscore` |
| Z-score anomaly path | **FALLBACK ONLY** | Explicit env opt-in; labeled `zscore_fallback` |
| MCP servers (5 tools) | **IMPLEMENTED + VERIFIED** | Import + handler tests |
| Safe SQL (no arbitrary LLM SQL) | **IMPLEMENTED + VERIFIED** | Parameterized templates only |
| LangGraph investigation agent | **IMPLEMENTED + VERIFIED** | Planner → tools → evidence → report |
| Month resolution (12% / explicit / auto) | **IMPLEMENTED + VERIFIED** | Does not silently replace 12% with worst month |
| Groq LLM provider | **IMPLEMENTED + VERIFIED** | Live probe when `GROQ_API_KEY` configured |
| Deterministic report path | **FALLBACK ONLY** | Active when `GROQ_API_KEY` missing; labeled `deterministic_fallback` |
| pgvector RAG (vector type + retrieval) | **IMPLEMENTED + ENVIRONMENT-LIMITED** | Verified via Docker `:5433`; local host PG uses JSON |
| JSON embedding RAG | **FALLBACK ONLY** | Documented; `retrieval_backend: json_fallback` locally |
| FastAPI + JWT auth | **IMPLEMENTED + VERIFIED** | Env-based `JWT_SECRET` / admin creds; no hardcoded `admin`/`marketlens123` |
| Next.js dashboard | **IMPLEMENTED + VERIFIED** | `npm run build` PASS; API smoke (auth, KPIs, forecast, anomaly, investigate + evidence IDs) |
| Full Docker Compose stack on host `:5432` | **IMPLEMENTED + ENVIRONMENT-LIMITED** | Compose exists; host port often occupied by other Postgres |
| Cloud deploy / MLflow / multi-tenant | **NOT IMPLEMENTED** | Out of v1 scope |

---

## Critical fixes — verification detail

### 1. Isolation Forest
- Detector name returned by pipeline: `isolation_forest`
- Injected anomaly validation: **injection_total=13, injection_hits=4**, anomalies flagged=59
- Not substituted with z-score unless explicitly configured

### 2. pgvector
- Primary path: `CREATE EXTENSION vector`, `embedding_vector vector(384)`, cosine retrieval
- Proven via `docker-compose.pgvector-test.yml` on host port **5433**
- Local default Postgres: **no** pgvector → JSON fallback only (explicitly labeled)

### 3. LLM integration
- Provider: **Groq only** (`GROQ_API_KEY`, `GROQ_MODEL`)
- Fallback: `deterministic_fallback` when `GROQ_API_KEY` is not configured
- Flow: question → planner → MCP tools → evidence bundle → report agent
- Constraints enforced: no invented numbers without evidence IDs; no raw SQL execution by LLM

### 4. Flagship question
- “We missed the sales target by 12%…” → **2019-02-01**, aggregate variance ≈ **-11.87%** (`percent_match`)
- Does **not** pick 2018-07-01 (−61.64%) unless auto/worst mode is requested
- Evidence IDs include e.g. `VARIANCE_2019-02-01`, `Q_revenue_by_state`, `ANOMALY_state`

### 5. Auth
- Required env: `JWT_SECRET`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`
- `.env.example` documents placeholders only
- README no longer advertises hardcoded `admin` / `marketlens123`

---

## Sample ML metrics (actual DB)

Clothing (representative):

| Horizon | Model | MAE | MAPE | Samples |
|---------|-------|-----|------|---------|
| 7d | prophet | 1198.41 | 31.58% | 22 |
| 7d | naive_baseline | 1269.21 | 33.03% | 22 |
| 7d | xgboost | 1727.30 | 50.68% | 22 |
| 30d | prophet | 1860.96 | 14.84% | 3 |
| 30d | naive_baseline | 1990.40 | 15.32% | 3 |
| 30d | xgboost | 7398.27 | 55.82% | 3 |

---

## Reproduce complete stack

```powershell
# From project root
Copy-Item .env.example .env   # then edit JWT_SECRET, ADMIN_*, optional LLM keys
pip install -r requirements.txt
python scripts/setup_db.py
python scripts/etl/load_data.py
python -m backend.app.ml.pipeline
python -m backend.app.rag

# API
uvicorn backend.app.main:app --reload --port 8000

# UI
cd frontend; npm install; npm run dev

# Tests
pytest tests/ -v
cd frontend; npm run build

# pgvector primary path (avoids :5432 conflict)
docker compose -f docker-compose.pgvector-test.yml up -d
pytest tests/test_pgvector_docker.py -v
```

Optional live LLM: set `GROQ_API_KEY` and `GROQ_MODEL` in `.env`.

---

## Exact limitations (do not overclaim)

1. Host Postgres without `vector` → RAG is **FALLBACK ONLY** (`json_fallback`).
2. No `GROQ_API_KEY` → report path is **FALLBACK ONLY** (`deterministic_fallback`), not live Groq.
3. Single fiscal year of sales data; 90-day forecasts are experimental.
4. Full `docker compose` on `:5432` may conflict with other local Postgres instances; use `:5433` pgvector-test compose for vector verification.
5. Isolation Forest injection recall here is **4/13** — real IF, not perfect detection.
