"""FastAPI application for MarketLens AI."""

from __future__ import annotations

import logging

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import text

from backend.app.agent.graph import run_investigation
from backend.app.config import Settings, get_settings
from backend.app.auth.jwt_auth import (
    authenticate_user,
    create_access_token,
    ensure_default_user,
    require_auth,
)
from backend.app.database import get_engine, pgvector_available
from backend.app.llm.provider import llm_status
from backend.app.ml.sklearn_runtime import active_detector_name, isolation_forest_available
from backend.app.ml.anomaly import get_anomalies
from backend.app.ml.drift import run_drift_check
from backend.app.ml.forecast import get_forecast
from backend.app.ml.pipeline import run_ml_pipeline
from backend.app.ml.variance import get_monthly_summary, get_variance
from backend.app.query.safe_sql import QueryTemplate, SqlQuerySpec, execute_safe_query
from backend.app.rag.search import get_rag_backend, ingest_documents
from backend.app.investigation.month_resolver import RESOLVER_MODULE, RESOLVER_VERSION
from backend.app.tools.handlers import handle_rag_search

logger = logging.getLogger(__name__)

app = FastAPI(title="MarketLens AI", version="1.0.0")


def _configure_cors(application: FastAPI, settings: Settings) -> None:
    origins = settings.cors_allowed_origins_list
    if origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        return
    application.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


_configure_cors(app, get_settings())


class LoginRequest(BaseModel):
    username: str
    password: str


class InvestigateRequest(BaseModel):
    question: str = Field(min_length=5)
    context_month: str | None = None


class RagRequest(BaseModel):
    query: str
    top_k: int = 5


@app.on_event("startup")
def startup() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    logger.info(
        "startup resolver_version=%s resolver_module=%s",
        RESOLVER_VERSION,
        RESOLVER_MODULE,
    )
    get_settings.cache_clear()
    ensure_default_user()


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "marketlens-ai",
        "resolver_version": RESOLVER_VERSION,
        "resolver_module": RESOLVER_MODULE,
    }


@app.get("/api/system/status")
def system_status(_: str = Depends(require_auth)):
    return {
        "anomaly_detector": active_detector_name(),
        "isolation_forest_available": isolation_forest_available(probe=True),
        "rag_backend": get_rag_backend(),
        "pgvector_available": pgvector_available(),
        "llm": llm_status(),
    }


@app.post("/auth/login")
def login(body: LoginRequest):
    if not authenticate_user(body.username, body.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"access_token": create_access_token(body.username), "token_type": "bearer"}


@app.get("/api/kpis")
def kpis(_: str = Depends(require_auth)):
    engine = get_engine()
    with engine.connect() as conn:
        revenue = conn.execute(
            text("SELECT COALESCE(SUM(amount),0) FROM order_details")
        ).scalar()
        targets = conn.execute(
            text("SELECT COALESCE(SUM(target_amount),0) FROM sales_targets")
        ).scalar()
        anomalies = conn.execute(
            text("SELECT COUNT(*) FROM anomaly_flags WHERE is_anomaly = TRUE")
        ).scalar()
    variance_rows = get_variance()
    total_actual = sum(float(r["actual_amount"]) for r in variance_rows)
    total_target = sum(float(r["target_amount"]) for r in variance_rows)
    variance_pct = (
        (total_actual - total_target) / total_target * 100 if total_target else 0
    )
    return {
        "revenue": float(revenue),
        "target_total": float(targets),
        "variance_pct": round(variance_pct, 2),
        "active_anomalies": int(anomalies),
    }


@app.get("/api/variance")
def variance(month: str | None = None, _: str = Depends(require_auth)):
    if month:
        return get_monthly_summary(month)
    return get_variance()


@app.get("/api/forecasts/{category}")
def forecasts(category: str, horizon: int = 30, model: str = "xgboost", _: str = Depends(require_auth)):
    return get_forecast(category, horizon, model)


@app.get("/api/anomalies")
def anomalies(dimension: str = "state", _: str = Depends(require_auth)):
    return get_anomalies(dimension, only_anomalies=True)


@app.get("/api/insights")
def insights(_: str = Depends(require_auth)):
    variance_rows = get_variance()
    worst = min(variance_rows, key=lambda r: float(r["variance_pct"])) if variance_rows else None
    anomalies = get_anomalies("state", only_anomalies=True)[:3]
    items = []
    if worst:
        items.append(
            {
                "type": "variance",
                "message": (
                    f"{worst['category']} missed target by "
                    f"{float(worst['variance_pct']):.1f}% in {worst['target_month']}"
                ),
                "evidence_id": f"VARIANCE_{worst['target_month']}",
            }
        )
    for a in anomalies:
        items.append(
            {
                "type": "anomaly",
                "message": (
                    f"Revenue anomaly flagged for {a['dimension_value']} on {a['anomaly_date']}"
                ),
                "evidence_id": f"ANOMALY_{a['anomaly_id']}",
            }
        )
    return items


@app.post("/api/investigate")
def investigate(body: InvestigateRequest, _: str = Depends(require_auth)):
    logger.info(
        "investigate.request question_len=%d context_month=%s resolver_version=%s",
        len(body.question),
        body.context_month or "(none)",
        RESOLVER_VERSION,
    )
    try:
        result = run_investigation(body.question, context_month=body.context_month)
        logger.info(
            "investigate.success target_month=%s mode=%s",
            result.get("target_month"),
            (result.get("month_resolution") or {}).get("mode"),
        )
        if isinstance(result.get("month_resolution"), dict):
            result["month_resolution"]["resolver_version"] = RESOLVER_VERSION
        return result
    except ValueError as exc:
        logger.warning(
            "investigate.value_error type=%s message=%s",
            exc.__class__.__name__,
            str(exc),
        )
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception(
            "investigate.unhandled type=%s message=%s",
            exc.__class__.__name__,
            str(exc),
        )
        raise HTTPException(
            status_code=500,
            detail=f"Investigation failed: {exc.__class__.__name__}",
        ) from exc


@app.post("/api/rag/search")
def rag_search(body: RagRequest, _: str = Depends(require_auth)):
    return handle_rag_search(body.query, body.top_k)


@app.post("/api/admin/run-ml-pipeline")
def admin_run_ml(_: str = Depends(require_auth)):
    return run_ml_pipeline()


@app.post("/api/admin/run-drift-check")
def admin_drift(_: str = Depends(require_auth)):
    return run_drift_check()


@app.get("/api/drilldown/states")
def states(month: str | None = None, category: str | None = None, _: str = Depends(require_auth)):
    spec = SqlQuerySpec(
        template=QueryTemplate.REVENUE_BY_STATE,
        start_date=month,
        end_date=month,
        category=category,
    )
    return execute_safe_query(spec)
