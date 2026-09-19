import { formatCurrency, formatPercent, isNegativeMetric } from "@/lib/format";

type KpiCardProps = {
  label: string;
  value: string;
  subtext?: string;
  trend?: number;
  loading?: boolean;
};

export function KpiCard({ label, value, subtext, trend, loading }: KpiCardProps) {
  if (loading) {
    return (
      <div className="card-compact">
        <div className="skeleton mb-2 h-3 w-16" />
        <div className="skeleton h-7 w-24" />
      </div>
    );
  }

  const trendClass =
    trend != null
      ? isNegativeMetric(trend)
        ? "metric-negative"
        : trend > 0
          ? "metric-positive"
          : "text-muted"
      : "";

  return (
    <div className="card-compact animate-fade-in transition-shadow hover:shadow-elevated">
      <p className="text-xs font-medium uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-1 font-display text-2xl font-semibold tracking-tight text-ink">
        {value}
      </p>
      {subtext && (
        <p className={`mt-1 text-xs ${trendClass || "text-muted"}`}>{subtext}</p>
      )}
    </div>
  );
}

export function buildKpiCards(kpis: {
  revenue: number;
  target_total: number;
  variance_pct: number;
  active_anomalies: number;
}) {
  return [
    {
      label: "Revenue",
      value: formatCurrency(kpis.revenue),
      subtext: `vs target ${formatPercent(kpis.variance_pct)}`,
      trend: kpis.variance_pct,
    },
    {
      label: "Target",
      value: formatCurrency(kpis.target_total),
      subtext: "Total sales target",
    },
    {
      label: "Variance",
      value: formatPercent(kpis.variance_pct),
      subtext: kpis.variance_pct < 0 ? "Below target" : kpis.variance_pct > 0 ? "Above target" : "On target",
      trend: kpis.variance_pct,
    },
    {
      label: "Anomalies",
      value: String(kpis.active_anomalies),
      subtext: "Unusual signals detected",
    },
  ];
}
