"use client";

import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatCurrency, formatMonth } from "@/lib/format";
import type { ForecastPoint, VarianceRow } from "@/lib/types";

type ForecastSectionProps = {
  category: string;
  forecasts: ForecastPoint[];
  historical: VarianceRow[];
  targetTotal: number;
  loading?: boolean;
  onViewDetails?: () => void;
};

export function ForecastSection({
  category,
  forecasts,
  historical,
  targetTotal,
  loading,
  onViewDetails,
}: ForecastSectionProps) {
  if (loading) {
    return (
      <div className="card">
        <div className="skeleton mb-4 h-5 w-32" />
        <div className="skeleton h-64 w-full" />
      </div>
    );
  }

  const histByMonth = new Map<string, number>();
  for (const row of historical.filter((r) => r.category === category)) {
    const key = String(row.target_month).slice(0, 10);
    histByMonth.set(key, Number(row.actual_amount));
  }

  const histPoints = [...histByMonth.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([month, actual]) => ({
      date: month,
      label: formatMonth(month),
      actual,
      forecast: null as number | null,
      target: targetTotal / Math.max(histByMonth.size, 1),
      type: "historical" as const,
    }));

  const forecastPoints = forecasts.map((f) => ({
    date: String(f.forecast_date).slice(0, 10),
    label: formatMonth(String(f.forecast_date)),
    actual: null as number | null,
    forecast: Number(f.predicted_value),
    target: targetTotal / Math.max(forecasts.length, 1),
    type: "forecast" as const,
  }));

  const chartData = [...histPoints, ...forecastPoints];
  const forecastTotal = forecasts.reduce((s, p) => s + Number(p.predicted_value), 0);
  const delta = forecastTotal - targetTotal;
  const model = forecasts[0]?.model_name ?? "xgboost";
  const horizon = forecasts.length;

  const forecastStart = forecastPoints[0]?.date;

  return (
    <section className="card space-y-4">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="font-display text-base font-semibold">Forecast</h2>
          <p className="text-xs text-muted">
            {category} • {model} • {horizon}-day horizon
          </p>
        </div>
        {onViewDetails && (
          <button type="button" onClick={onViewDetails} className="btn-compact">
            View forecast details →
          </button>
        )}
      </div>

      {chartData.length === 0 ? (
        <p className="text-sm text-muted">No forecast data available.</p>
      ) : (
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
              <XAxis
                dataKey="label"
                tick={{ fontSize: 10, fill: "var(--muted)" }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 10, fill: "var(--muted)" }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => formatCurrency(v)}
                width={52}
              />
              <Tooltip
                contentStyle={{
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                  borderRadius: 8,
                  fontSize: 12,
                }}
                formatter={(value: number, name: string) => [
                  formatCurrency(value),
                  name,
                ]}
              />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              {forecastStart && (
                <ReferenceArea
                  x1={forecastPoints[0]?.label}
                  x2={forecastPoints[forecastPoints.length - 1]?.label}
                  fill="var(--accent-muted)"
                  fillOpacity={0.4}
                />
              )}
              <Line
                type="monotone"
                dataKey="actual"
                name="Historical actual"
                stroke="var(--accent)"
                strokeWidth={2}
                dot={false}
                connectNulls={false}
              />
              <Area
                type="monotone"
                dataKey="forecast"
                name="Forecast"
                stroke="var(--warning)"
                fill="var(--warning)"
                fillOpacity={0.15}
                strokeWidth={2}
                dot={false}
                connectNulls={false}
              />
              <Line
                type="monotone"
                dataKey="target"
                name="Target"
                stroke="var(--muted)"
                strokeDasharray="4 4"
                strokeWidth={1.5}
                dot={false}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="rounded-xl border border-border bg-accent-muted/30 p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted">
          Forecast risk
        </p>
        <p className="mt-1 text-sm text-ink">
          {delta < 0
            ? `${category} is projected to remain ${formatCurrency(Math.abs(delta))} below target over the selected horizon.`
            : `${category} is projected to meet or exceed target over the selected horizon.`}
        </p>
      </div>
    </section>
  );
}
