# Phase 0 — Data Profile Report

Generated from **actual** CSV files in `data/raw/`. Source files were not modified.

## Files Found

| Filename | Size | Raw Rows | Valid Rows |
|----------|------|----------|------------|
| `List of Orders.csv` | 23.6 KB | 560 | **500** |
| `Order Details.csv` | 63.6 KB | 1500 | **1500** |
| `Sales target.csv` | 1.0 KB | 36 | **36** |

## Column Mapping (Spec vs Actual)

| Spec Column | Actual CSV Column | Postgres Column |
|-------------|-------------------|-----------------|
| `customer_name` | `CustomerName` | `customer_name` |
| `customer_state` | `State` | `customer_state` |
| `customer_city` | `City` | `customer_city` |
| `price` | **`Amount`** | `amount` |
| `target_amount` | **`Target`** | `target_amount` |
| `month` | **`Month of Order Date`** (MMM-YY string) | `target_month` (DATE, 1st of month) |

No missing columns. All relationships described in the spec exist in the data.

## Date Range

- **Minimum:** 2018-04-01
- **Maximum:** 2019-03-31
- **Format in source:** `DD-MM-YYYY` (e.g. `01-04-2018`)

## Categories

`Clothing`, `Electronics`, `Furniture` — identical across Order Details and Sales Target (3 categories, 17 sub-categories).

## Join Integrity

| Check | Result |
|-------|--------|
| Order IDs in details ⊆ orders (valid rows) | **PASS** — 0 orphans |
| Order IDs in orders ⊆ details | **PASS** — 500/500 matched |
| Categories details ↔ targets | **PASS** — exact match |
| Actual sales months ↔ target months | **PASS** — all 36 category-month combos joinable |

## Target Table Grain

- **Grain:** one row per `(Month of Order Date, Category)`
- **Month format:** `MMM-YY` (e.g. `Apr-18`, `Jan-19`)
- **Rows:** 36 = 12 months × 3 categories
- **Duplicates:** 0

## Data Quality Issues

| Issue | Count | ETL Handling |
|-------|-------|--------------|
| Trailing blank rows in Orders CSV | 60 | Dropped (`Order ID` IS NULL) |
| Trailing whitespace on `Kerala` state | 1 value | `str.strip()` |
| Real customer names in source | 332 unique | Stored for joins; **not for UI display** |
| Negative profit values | Present | Loaded as-is (valid business data) |

## Spec Discrepancies (Naming Only)

The data **supports** the spec's relational model. Only column **names** differ from the build document — mapped explicitly in ETL. No fabricated columns or relationships.

## Festival Calendar

- **Source:** `data/reference/festival_calendar.csv` (curated reference, not transactional)
- **Coverage:** 2018-04-14 through 2019-03-21 (spans full sales date range)
- **Entries:** 18 festivals/holidays including Diwali, Holi, Eid, Independence Day, Republic Day

## PostgreSQL Schema

See `sql/schema.sql`:

- `orders` (500 rows)
- `order_details` (1500 rows)
- `sales_targets` (36 rows)
- `festival_calendar` (18 rows)
- `etl_run_log` (audit)

## Re-run Profiling

```bash
python scripts/profile_data.py
```
