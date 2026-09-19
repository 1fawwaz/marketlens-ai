import type { ExecutiveInsight } from "@/lib/types";
import { isNegativeMetric } from "@/lib/format";

const TYPE_STYLES: Record<string, string> = {
  "TARGET MISS": "bg-negative-muted text-negative",
  ANOMALY: "bg-amber-500/10 text-warning",
  FORECAST: "bg-accent-muted text-accent",
  OPPORTUNITY: "bg-positive-muted text-positive",
};

type InsightCardProps = {
  insight: ExecutiveInsight;
  onInvestigate: (insight: ExecutiveInsight) => void;
  onViewEvidence: (insight: ExecutiveInsight) => void;
  compact?: boolean;
};

export function InsightCard({
  insight,
  onInvestigate,
  onViewEvidence,
  compact,
}: InsightCardProps) {
  const metricClass = isNegativeMetric(insight.metricValue)
    ? "metric-negative"
    : insight.metricValue > 0
      ? "metric-positive"
      : "text-ink";

  return (
    <article
      className={`group relative overflow-hidden rounded-xl border border-border bg-surface p-4 transition-all hover:border-accent hover:shadow-card ${
        compact ? "" : "animate-slide-up"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <span
          className={`insight-label ${TYPE_STYLES[insight.type] ?? "bg-accent-muted text-accent"}`}
        >
          {insight.type}
        </span>
        <button
          type="button"
          onClick={() => onViewEvidence(insight)}
          className="text-[10px] font-medium text-muted underline-offset-2 hover:text-accent hover:underline"
        >
          Evidence-backed
        </button>
      </div>

      <h3 className="mt-2 font-display text-sm font-semibold leading-snug text-ink">
        {insight.headline}
      </h3>
      <p className="mt-1 text-xs leading-relaxed text-muted">{insight.explanation}</p>

      <div className="mt-3 flex items-end justify-between gap-2">
        <div>
          <p className={`font-display text-2xl font-bold tracking-tight ${metricClass}`}>
            {insight.metric}
          </p>
          <p className="mt-0.5 text-[11px] text-muted">{insight.context}</p>
        </div>
        <button
          type="button"
          onClick={() => onInvestigate(insight)}
          className="btn-compact shrink-0"
        >
          Investigate →
        </button>
      </div>
    </article>
  );
}
