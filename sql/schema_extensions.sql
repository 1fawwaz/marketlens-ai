-- Phase 1+ schema extensions (applied after schema.sql)

-- Daily sales materialized for ML features
CREATE TABLE IF NOT EXISTS daily_category_sales (
    sales_date      DATE         NOT NULL,
    category        VARCHAR(50)  NOT NULL,
    revenue         NUMERIC(14, 2) NOT NULL DEFAULT 0,
    order_count     INTEGER      NOT NULL DEFAULT 0,
    quantity        INTEGER      NOT NULL DEFAULT 0,
    profit          NUMERIC(14, 2) NOT NULL DEFAULT 0,
    computed_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (sales_date, category)
);

CREATE INDEX IF NOT EXISTS idx_daily_category_sales_category ON daily_category_sales (category);

-- Forecast outputs
CREATE TABLE IF NOT EXISTS forecast_results (
    forecast_id     BIGSERIAL    PRIMARY KEY,
    category        VARCHAR(50)  NOT NULL,
    model_name      VARCHAR(50)  NOT NULL,
    horizon_days    INTEGER      NOT NULL,
    forecast_date   DATE         NOT NULL,
    predicted_value NUMERIC(14, 2) NOT NULL,
    is_experimental BOOLEAN      NOT NULL DEFAULT FALSE,
    generated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (category, model_name, horizon_days, forecast_date)
);

CREATE INDEX IF NOT EXISTS idx_forecast_results_lookup
    ON forecast_results (category, model_name, horizon_days);

-- Forecast evaluation metrics
CREATE TABLE IF NOT EXISTS forecast_evaluations (
    eval_id         BIGSERIAL    PRIMARY KEY,
    category        VARCHAR(50)  NOT NULL,
    model_name      VARCHAR(50)  NOT NULL,
    horizon_days    INTEGER      NOT NULL,
    mae             NUMERIC(14, 4) NOT NULL,
    mape            NUMERIC(14, 4) NOT NULL,
    eval_samples    INTEGER      NOT NULL,
    evaluated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (category, model_name, horizon_days)
);

-- Anomaly flags
CREATE TABLE IF NOT EXISTS anomaly_flags (
    anomaly_id      BIGSERIAL    PRIMARY KEY,
    dimension_type  VARCHAR(30)  NOT NULL,
    dimension_value VARCHAR(100) NOT NULL,
    anomaly_date    DATE         NOT NULL,
    metric_name     VARCHAR(50)  NOT NULL,
    metric_value    NUMERIC(14, 2) NOT NULL,
    anomaly_score   NUMERIC(10, 6) NOT NULL,
    is_anomaly      BOOLEAN      NOT NULL,
    is_injected     BOOLEAN      NOT NULL DEFAULT FALSE,
    detected_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (dimension_type, dimension_value, anomaly_date, metric_name)
);

CREATE INDEX IF NOT EXISTS idx_anomaly_flags_lookup
    ON anomaly_flags (dimension_type, anomaly_date, is_anomaly);

-- Variance analysis snapshots (target achievement engine)
CREATE TABLE IF NOT EXISTS variance_snapshots (
    snapshot_id     BIGSERIAL    PRIMARY KEY,
    target_month    DATE         NOT NULL,
    category        VARCHAR(50)  NOT NULL,
    target_amount   NUMERIC(14, 2) NOT NULL,
    actual_amount   NUMERIC(14, 2) NOT NULL,
    variance_amount NUMERIC(14, 2) NOT NULL,
    variance_pct    NUMERIC(10, 4) NOT NULL,
    top_state       VARCHAR(50),
    top_state_amount NUMERIC(14, 2),
    computed_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (target_month, category)
);

-- Phase 4 — RAG document store (pgvector optional; embedding_json fallback)
CREATE TABLE IF NOT EXISTS rag_documents (
    doc_id          SERIAL       PRIMARY KEY,
    doc_name        VARCHAR(200) NOT NULL,
    section_title   VARCHAR(200) NOT NULL,
    chunk_text      TEXT         NOT NULL,
    is_synthetic    BOOLEAN      NOT NULL DEFAULT TRUE,
    embedding_json  JSONB,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (doc_name, section_title)
);

-- Phase 6 — forecast drift monitoring
CREATE TABLE IF NOT EXISTS forecast_drift_log (
    drift_id        BIGSERIAL    PRIMARY KEY,
    category        VARCHAR(50)  NOT NULL,
    model_name      VARCHAR(50)  NOT NULL,
    horizon_days    INTEGER      NOT NULL,
    window_start    DATE         NOT NULL,
    window_end      DATE         NOT NULL,
    mae             NUMERIC(14, 4) NOT NULL,
    baseline_mae    NUMERIC(14, 4) NOT NULL,
    drift_ratio     NUMERIC(10, 4) NOT NULL,
    is_degraded     BOOLEAN      NOT NULL,
    logged_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Phase 6 — auth users (single tenant)
CREATE TABLE IF NOT EXISTS app_users (
    user_id         SERIAL       PRIMARY KEY,
    username        VARCHAR(100) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
