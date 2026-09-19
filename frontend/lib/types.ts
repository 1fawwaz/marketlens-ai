export type Kpis = {
  revenue: number;
  target_total: number;
  variance_pct: number;
  active_anomalies: number;
};

export type VarianceRow = {
  snapshot_id: number;
  target_month: string;
  category: string;
  target_amount: number;
  actual_amount: number;
  variance_amount: number;
  variance_pct: number;
  top_state: string | null;
  top_state_amount: number | null;
};

export type MonthlySummary = {
  target_month: string;
  total_target: number;
  total_actual: number;
  variance_amount: number;
  variance_pct: number;
  largest_miss_category: string;
  largest_miss_variance_pct: number;
  largest_state: string;
  by_category: VarianceRow[];
};

export type RawInsight = {
  type: string;
  message: string;
  evidence_id: string;
};

export type InsightType = "TARGET MISS" | "ANOMALY" | "FORECAST" | "OPPORTUNITY";

export type ExecutiveInsight = {
  id: string;
  type: InsightType;
  headline: string;
  explanation: string;
  metric: string;
  metricValue: number;
  context: string;
  evidenceId: string;
  evidenceTool: string;
  priority: number;
  evidenceDetails?: Record<string, unknown>;
};

export type Anomaly = {
  anomaly_id: number;
  dimension_type: string;
  dimension_value: string;
  anomaly_date: string;
  metric_name: string;
  metric_value: number;
  anomaly_score: number;
  is_anomaly: boolean;
  is_injected: boolean;
};

export type ForecastPoint = {
  forecast_date: string;
  predicted_value: number;
  is_experimental: boolean;
  model_name: string;
};

export type SystemStatus = {
  anomaly_detector: string;
  isolation_forest_available: boolean;
  rag_backend: string;
  pgvector_available: boolean;
  llm: {
    provider?: string;
    available?: boolean;
  };
};

export type ForecastVsTarget = {
  grain: string;
  category: string;
  forecast_total: number;
  target_total: number;
  delta: number;
  model: string;
  horizon_days: number;
  is_experimental: boolean;
  comparison_note: string;
};

export type EvidenceBundle = {
  question?: string;
  target_month?: string;
  target?: number;
  actual?: number;
  variance_amount?: number;
  variance_pct?: number;
  largest_miss_category?: string;
  largest_miss_variance_pct?: number;
  largest_contributing_region?: string;
  forecast_vs_target?: ForecastVsTarget | null;
  relevant_festivals?: unknown[];
  anomaly_signals?: Anomaly[];
  supporting_query_ids?: string[];
  region_breakdown?: { customer_state?: string; total_amount?: number }[];
  notes?: string[];
};

export type ToolResult = {
  tool: string;
  template?: string;
  payload?: {
    query_id?: string;
    provenance?: { query_id?: string; source?: string };
    summary?: MonthlySummary;
    rows?: unknown[];
    anomalies?: Anomaly[];
    category?: string;
    model_name?: string;
    horizon_days?: number;
    forecast_total?: number;
    is_experimental?: boolean;
  };
};

export type InvestigationResult = {
  question: string;
  report: string;
  target_month: string;
  month_resolution: {
    mode: string;
    matched_variance_pct?: number;
    requested_variance_pct?: number;
  };
  evidence_bundle: EvidenceBundle;
  report_provider: string;
  planner_provider?: string;
  tool_results?: ToolResult[];
};

export type DashboardFilters = {
  month: string;
  category: string;
  state: string;
  metric: "revenue" | "variance";
};

export type NavSection =
  | "overview"
  | "target"
  | "forecasts"
  | "anomalies"
  | "investigations";

export type MonthlyChartPoint = {
  month: string;
  monthLabel: string;
  actual: number;
  target: number;
  variancePct: number;
};

export type ChartSummary = {
  largestMissCategory: string;
  categoryHighlightLabel: string;
  categoryHighlightVariancePct: number;
  worstMonth: string;
  worstMonthLabel: string;
};
