import { InsightCard } from "@/components/ui/InsightCard";
import type { ExecutiveInsight } from "@/lib/types";

type InsightsSectionProps = {
  insights: ExecutiveInsight[];
  loading?: boolean;
  showAll?: boolean;
  onInvestigate: (insight: ExecutiveInsight) => void;
  onViewEvidence: (insight: ExecutiveInsight) => void;
  onViewAll?: () => void;
};

export function InsightsSection({
  insights,
  loading,
  showAll,
  onInvestigate,
  onViewEvidence,
  onViewAll,
}: InsightsSectionProps) {
  const visible = showAll ? insights : insights.slice(0, 4);

  return (
    <section className="space-y-4">
      <div className="flex items-end justify-between">
        <div>
          <h2 className="font-display text-lg font-semibold">AI Insights</h2>
          <p className="text-sm text-muted">
            Prioritized signals from variance, forecast, and anomaly analysis
          </p>
        </div>
        {!showAll && insights.length > 4 && onViewAll && (
          <button type="button" onClick={onViewAll} className="btn-compact">
            View all insights →
          </button>
        )}
      </div>

      {loading ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="card-compact">
              <div className="skeleton mb-2 h-3 w-20" />
              <div className="skeleton mb-2 h-4 w-full" />
              <div className="skeleton h-8 w-16" />
            </div>
          ))}
        </div>
      ) : visible.length === 0 ? (
        <div className="card text-sm text-muted">No insights for the current filters.</div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {visible.map((insight) => (
            <InsightCard
              key={insight.id}
              insight={insight}
              onInvestigate={onInvestigate}
              onViewEvidence={onViewEvidence}
            />
          ))}
        </div>
      )}
    </section>
  );
}
