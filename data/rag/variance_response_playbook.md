# Variance Response Playbook (Synthetic)

> **SYNTHETIC DOCUMENT** — Created for MarketLens AI demo purposes.

## 12% Aggregate Miss Threshold

An aggregate miss at or above 12% triggers a structured investigation. The response must cite evidence from SQL variance results, forecast comparisons, and anomaly signals.

## Regional Contribution Analysis

Identify the state with the largest revenue contribution within the missed month. This is a descriptive drill-down, not automatic root-cause attribution.

## Festival Context

Festivals may coincide with demand spikes or lulls. Use the festival calendar as contextual association only unless supported by category-specific historical patterns.

## Documentation Requirements

Every numeric claim in an investigation report must reference the tool/query identifier that produced it (e.g., VARIANCE_2018-11-01, Q_revenue_by_state).
