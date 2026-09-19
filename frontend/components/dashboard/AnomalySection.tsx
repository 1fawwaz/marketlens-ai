import { formatCurrency, formatShortDate } from "@/lib/format";
import type { Anomaly } from "@/lib/types";

type AnomalySectionProps = {
  anomalies: Anomaly[];
  loading?: boolean;
  limit?: number;
};

function severityLabel(score: number): string {
  if (score >= 0.8) return "High";
  if (score >= 0.5) return "Medium";
  return "Low";
}

export function AnomalySection({ anomalies, loading, limit = 6 }: AnomalySectionProps) {
  const top = anomalies.slice(0, limit);

  if (loading) {
    return (
      <section className="card space-y-3">
        <div className="skeleton h-5 w-40" />
        {[1, 2, 3].map((i) => (
          <div key={i} className="skeleton h-12 w-full" />
        ))}
      </section>
    );
  }

  return (
    <section className="card space-y-4">
      <div>
        <h2 className="font-display text-base font-semibold">
          {anomalies.length} unusual signal{anomalies.length !== 1 ? "s" : ""} detected
        </h2>
        <p className="text-xs text-muted">
          Statistical outliers across dimensions — not causal proof
        </p>
      </div>

      {top.length === 0 ? (
        <p className="text-sm text-muted">No anomalies detected for the current period.</p>
      ) : (
        <ul className="space-y-2">
          {top.map((a) => (
            <li
              key={a.anomaly_id}
              className="flex items-center justify-between gap-3 rounded-lg border border-border bg-surface-elevated px-3 py-2.5 transition-colors hover:border-accent"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-ink">
                  {a.dimension_value}
                  <span className="mx-1.5 text-muted">•</span>
                  <span className="text-muted">{formatShortDate(String(a.anomaly_date))}</span>
                </p>
                <p className="text-xs text-muted">
                  {a.dimension_type} • {a.metric_name.replace(/_/g, " ")} •{" "}
                  {formatCurrency(a.metric_value)}
                </p>
              </div>
              <div className="shrink-0 text-right">
                <p className="text-xs font-semibold text-warning">
                  {severityLabel(a.anomaly_score)}
                </p>
                <p className="font-mono text-[10px] text-muted">
                  {a.anomaly_score.toFixed(2)}
                </p>
              </div>
            </li>
          ))}
        </ul>
      )}

      <p className="rounded-lg bg-panel px-3 py-2 text-xs text-muted">
        <strong className="text-ink-secondary">Anomaly ≠ causal proof.</strong> These signals
        highlight unusual patterns worth investigating, not confirmed root causes.
      </p>
    </section>
  );
}
