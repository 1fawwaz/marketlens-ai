"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatCurrency } from "@/lib/format";
import type { ChartSummary, MonthlyChartPoint } from "@/lib/types";

type VarianceChartProps = {
  data: MonthlyChartPoint[];
  summary: ChartSummary;
  loading?: boolean;
};

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  const actual = payload.find((p: any) => p.dataKey === "actual")?.value;
  const target = payload.find((p: any) => p.dataKey === "target")?.value;
  const variance =
    target > 0 ? (((actual - target) / target) * 100).toFixed(2) : "0";

  return (
    <div className="rounded-lg border border-border bg-surface px-3 py-2 shadow-elevated text-xs">
      <p className="font-medium text-ink">{label}</p>
      <p className="text-muted">Actual: {formatCurrency(actual)}</p>
      <p className="text-muted">Target: {formatCurrency(target)}</p>
      <p className={Number(variance) < 0 ? "metric-negative" : "metric-positive"}>
        Variance: {variance}%
      </p>
    </div>
  );
}

export function VarianceChart({ data, summary, loading }: VarianceChartProps) {
  if (loading) {
    return (
      <div className="card h-80">
        <div className="skeleton mb-4 h-5 w-48" />
        <div className="skeleton h-56 w-full" />
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="card flex h-80 items-center justify-center text-sm text-muted">
        No variance data for the selected filters.
      </div>
    );
  }

  return (
    <div className="card">
      <div className="mb-4 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="font-display text-base font-semibold">Actual vs Target</h2>
          <p className="text-xs text-muted">Monthly revenue performance trend</p>
        </div>
      </div>

      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
            <XAxis
              dataKey="monthLabel"
              tick={{ fontSize: 11, fill: "var(--muted)" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 11, fill: "var(--muted)" }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) => formatCurrency(v)}
              width={56}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: "var(--accent-muted)" }} />
            <Legend
              wrapperStyle={{ fontSize: 12, paddingTop: 12 }}
              formatter={(value) => (
                <span style={{ color: "var(--muted)" }}>{value}</span>
              )}
            />
            <Bar
              dataKey="actual"
              name="Actual"
              fill="var(--accent)"
              radius={[4, 4, 0, 0]}
              maxBarSize={40}
            />
            <Bar
              dataKey="target"
              name="Target"
              fill="var(--muted)"
              opacity={0.45}
              radius={[4, 4, 0, 0]}
              maxBarSize={40}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-4 flex flex-wrap gap-4 border-t border-border pt-4 text-sm">
        <div>
          <span className="text-muted">{summary.categoryHighlightLabel}: </span>
          <strong className="text-ink">{summary.largestMissCategory}</strong>
        </div>
        <div>
          <span className="text-muted">Worst month: </span>
          <strong className="text-ink">{summary.worstMonthLabel}</strong>
        </div>
      </div>
    </div>
  );
}
