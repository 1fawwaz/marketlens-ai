-- MarketLens AI — Phase 0 schema
-- Designed from verified raw CSV columns (not spec assumptions).
-- Note: pgvector extension deferred to Phase 4 (RAG). Enable via Docker Compose or install locally.

-- CREATE EXTENSION IF NOT EXISTS vector;  -- Phase 4: RAG embeddings

-- ---------------------------------------------------------------------------
-- orders: one row per valid order (source: List of Orders.csv)
-- Raw columns: Order ID, Order Date, CustomerName, State, City
-- ETL excludes 60 trailing blank rows in source file.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS orders (
    order_id        VARCHAR(20)  PRIMARY KEY,
    order_date      DATE         NOT NULL,
    customer_name   VARCHAR(100) NOT NULL,
    customer_state  VARCHAR(50)  NOT NULL,
    customer_city   VARCHAR(50)  NOT NULL,
    loaded_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_orders_order_date ON orders (order_date);
CREATE INDEX IF NOT EXISTS idx_orders_customer_state ON orders (customer_state);

-- ---------------------------------------------------------------------------
-- order_details: line items (source: Order Details.csv)
-- Raw columns: Order ID, Amount, Profit, Quantity, Category, Sub-Category
-- Note: source uses "Amount" not "price"; mapped to amount column.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS order_details (
    detail_id       BIGSERIAL    PRIMARY KEY,
    order_id        VARCHAR(20)  NOT NULL REFERENCES orders (order_id),
    category        VARCHAR(50)  NOT NULL,
    sub_category    VARCHAR(50)  NOT NULL,
    quantity        INTEGER      NOT NULL CHECK (quantity > 0),
    amount          NUMERIC(12, 2) NOT NULL,
    profit          NUMERIC(12, 2) NOT NULL,
    loaded_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_order_details_order_id ON order_details (order_id);
CREATE INDEX IF NOT EXISTS idx_order_details_category ON order_details (category);

-- ---------------------------------------------------------------------------
-- sales_targets: monthly targets by category (source: Sales target.csv)
-- Raw columns: Month of Order Date (MMM-YY), Category, Target
-- Grain: one row per (target_month, category) — 36 rows verified.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sales_targets (
    target_id       SERIAL       PRIMARY KEY,
    category        VARCHAR(50)  NOT NULL,
    target_month    DATE         NOT NULL,
    target_amount   NUMERIC(12, 2) NOT NULL CHECK (target_amount >= 0),
    loaded_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (category, target_month)
);

CREATE INDEX IF NOT EXISTS idx_sales_targets_month ON sales_targets (target_month);

-- ---------------------------------------------------------------------------
-- festival_calendar: India public/festival reference dates
-- Synthetic reference table — not from transactional CSVs.
-- Covers verified sales range: 2018-04-01 to 2019-03-31.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS festival_calendar (
    calendar_id     SERIAL       PRIMARY KEY,
    festival_date   DATE         NOT NULL,
    festival_name   VARCHAR(100) NOT NULL,
    region_scope    VARCHAR(50)  NOT NULL DEFAULT 'National',
    loaded_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (festival_date, festival_name)
);

CREATE INDEX IF NOT EXISTS idx_festival_calendar_date ON festival_calendar (festival_date);

-- ---------------------------------------------------------------------------
-- etl_run_log: idempotency / audit trail
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS etl_run_log (
    run_id          BIGSERIAL    PRIMARY KEY,
    pipeline_name   VARCHAR(100) NOT NULL,
    started_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ,
    rows_loaded     JSONB,
    status          VARCHAR(20)  NOT NULL DEFAULT 'running',
    message         TEXT
);
