import {
  formatCurrency,
  formatMonth,
  formatPercentCompact,
} from "./format";
import {
  categoryInsightExplanation,
  categoryInsightHeadline,
  chartCategoryHighlightLabel,
} from "./insightSemantics";
import type {
  Anomaly,
  ExecutiveInsight,
  ForecastPoint,
  InsightType,
  VarianceRow,
} from "./types";

function labelStyle(type: InsightType): number {
  switch (type) {
    case "TARGET MISS":
      return 100;
    case "OPPORTUNITY":
      return 90;
    case "ANOMALY":
      return 70;
    case "FORECAST":
      return 60;
    default:
      return 50;
  }
}

export function buildExecutiveInsights(
  variance: VarianceRow[],
  anomalies: Anomaly[],
  forecasts: ForecastPoint[],
  forecastCategory: string,
  forecastTarget?: number,
): ExecutiveInsight[] {
  const insights: ExecutiveInsight[] = [];

  const misses = [...variance]
    .filter((r) => Number(r.variance_pct) < 0)
    .sort((a, b) => Number(a.variance_pct) - Number(b.variance_pct));

  if (misses.length > 0) {
    const worst = misses[0];
    const month = formatMonth(String(worst.target_month));
    insights.push({
      id: `miss-${worst.snapshot_id}`,
      type: "TARGET MISS",
      headline: categoryInsightHeadline(worst.category, Number(worst.variance_pct)),
      explanation: categoryInsightExplanation(
        worst.category,
        Number(worst.variance_pct),
        month,
      ),
      metric: formatPercentCompact(Number(worst.variance_pct)),
      metricValue: Number(worst.variance_pct),
      context: `${month} • ${worst.category}`,
      evidenceId: `VARIANCE_${worst.target_month}`,
      evidenceTool: "variance",
      priority: labelStyle("TARGET MISS") + Math.abs(Number(worst.variance_pct)),
      evidenceDetails: { row: worst },
    });
  }

  const opportunities = [...variance]
    .filter((r) => Number(r.variance_pct) > 5)
    .sort((a, b) => Number(b.variance_pct) - Number(a.variance_pct))
    .slice(0, 2);

  for (const row of opportunities) {
    const month = formatMonth(String(row.target_month));
    insights.push({
      id: `opp-${row.snapshot_id}`,
      type: "OPPORTUNITY",
      headline: categoryInsightHeadline(row.category, Number(row.variance_pct)),
      explanation: categoryInsightExplanation(
        row.category,
        Number(row.variance_pct),
        month,
      ),
      metric: formatPercentCompact(Number(row.variance_pct)),
      metricValue: Number(row.variance_pct),
      context: `${month} • ${row.category}`,
      evidenceId: `VARIANCE_${row.target_month}`,
      evidenceTool: "variance",
      priority: labelStyle("OPPORTUNITY") + Number(row.variance_pct),
      evidenceDetails: { row },
    });
  }

  for (const a of anomalies.slice(0, 3)) {
    const date = formatMonth(String(a.anomaly_date));
    insights.push({
      id: `anomaly-${a.anomaly_id}`,
      type: "ANOMALY",
      headline: `${a.dimension_value} revenue showed an unusual signal`,
      explanation: `Unusual ${a.metric_name.replace(/_/g, " ")} detected on ${formatMonth(String(a.anomaly_date))}.`,
      metric: a.anomaly_score.toFixed(2),
      metricValue: -a.anomaly_score,
      context: `${a.dimension_value} • ${date}`,
      evidenceId: `ANOMALY_${a.anomaly_id}`,
      evidenceTool: "anomaly_check",
      priority: labelStyle("ANOMALY") + a.anomaly_score,
      evidenceDetails: { anomaly: a },
    });
  }

  if (forecasts.length > 0 && forecastTarget != null && forecastTarget > 0) {
    const forecastTotal = forecasts.reduce((s, p) => s + Number(p.predicted_value), 0);
    const deltaPct = ((forecastTotal - forecastTarget) / forecastTarget) * 100;
    const model = forecasts[0]?.model_name ?? "xgboost";
    const horizon = forecasts.length;

    if (deltaPct < -2) {
      insights.push({
        id: `forecast-${forecastCategory}`,
        type: "FORECAST",
        headline: `${horizon}-day ${forecastCategory} forecast is below target`,
        explanation: `${forecastCategory} is projected ${formatCurrency(forecastTotal - forecastTarget)} below target over the selected horizon.`,
        metric: formatPercentCompact(deltaPct),
        metricValue: deltaPct,
        context: `${forecastCategory} • ${model}`,
        evidenceId: `FORECAST_${forecastCategory}`,
        evidenceTool: "forecast",
        priority: labelStyle("FORECAST") + Math.abs(deltaPct),
        evidenceDetails: {
          forecastTotal,
          forecastTarget,
          model,
          horizon,
        },
      });
    }
  }

  return insights.sort((a, b) => b.priority - a.priority);
}

export function aggregateMonthlyChart(variance: VarianceRow[]) {
  const byMonth = new Map<string, { actual: number; target: number }>();

  for (const row of variance) {
    const key = String(row.target_month).slice(0, 10);
    const existing = byMonth.get(key) ?? { actual: 0, target: 0 };
    existing.actual += Number(row.actual_amount);
    existing.target += Number(row.target_amount);
    byMonth.set(key, existing);
  }

  const points = [...byMonth.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([month, data]) => {
      const variancePct =
        data.target > 0 ? ((data.actual - data.target) / data.target) * 100 : 0;
      return {
        month,
        monthLabel: formatMonth(month),
        actual: data.actual,
        target: data.target,
        variancePct,
      };
    });

  let largestMissCategory = "—";
  let categoryHighlightLabel = "Largest miss";
  let categoryHighlightVariancePct = 0;
  let worstMonth = "—";
  let worstMonthLabel = "—";

  if (variance.length > 0) {
    const worst = [...variance].sort(
      (a, b) => Number(a.variance_pct) - Number(b.variance_pct),
    )[0];
    largestMissCategory = worst.category;
    categoryHighlightVariancePct = Number(worst.variance_pct);
    categoryHighlightLabel = chartCategoryHighlightLabel(categoryHighlightVariancePct);
    worstMonth = String(worst.target_month);
    worstMonthLabel = formatMonth(worstMonth);
  }

  return {
    chartData: points,
    summary: {
      largestMissCategory,
      categoryHighlightLabel,
      categoryHighlightVariancePct,
      worstMonth,
      worstMonthLabel,
    },
  };
}

export function filterVariance(
  variance: VarianceRow[],
  filters: { month: string; category: string; state: string },
): VarianceRow[] {
  return variance.filter((row) => {
    if (filters.month && !String(row.target_month).startsWith(filters.month)) {
      return false;
    }
    if (filters.category && row.category !== filters.category) {
      return false;
    }
    if (filters.state && row.top_state !== filters.state) {
      return false;
    }
    return true;
  });
}

export function extractFilterOptions(variance: VarianceRow[], anomalies: Anomaly[]) {
  const months = [...new Set(variance.map((r) => monthKey(String(r.target_month))))].sort();
  const categories = [...new Set(variance.map((r) => r.category))].sort();
  const states = [
    ...new Set([
      ...variance.map((r) => r.top_state).filter(Boolean) as string[],
      ...anomalies.map((a) => a.dimension_value),
    ]),
  ].sort();

  return { months, categories, states };
}

function monthKey(iso: string) {
  return iso.slice(0, 7);
}
