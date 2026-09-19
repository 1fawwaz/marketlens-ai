"use client";

import { useEffect, useState } from "react";
import {
  formatCurrency,
  formatMonth,
  formatPercent,
  formatResolutionMode,
} from "@/lib/format";
import {
  categoryFactorDetail,
  categoryFactorTitle,
  regionalFactorTitle,
} from "@/lib/insightSemantics";
import type { InvestigationResult } from "@/lib/types";
import { LoadingPanel } from "@/components/ui/StatePanels";

const INVESTIGATION_STEPS = [
  "Target vs actual",
  "Category contribution",
  "Regional contribution",
  "Forecast",
  "Anomaly signals",
  "Preparing explanation",
];

type InvestigationPanelProps = {
  question: string;
  onQuestionChange: (q: string) => void;
  onRun: (question: string) => void;
  result: InvestigationResult | null;
  loading: boolean;
  error?: string;
  onViewEvidence: () => void;
};

export function InvestigationPanel({
  question,
  onQuestionChange,
  onRun,
  result,
  loading,
  error,
  onViewEvidence,
}: InvestigationPanelProps) {
  const [stepIndex, setStepIndex] = useState(0);
  const [showTechnical, setShowTechnical] = useState(false);

  useEffect(() => {
    if (!loading) {
      setStepIndex(0);
      return;
    }
    setShowTechnical(false);
    setStepIndex(0);
    const interval = setInterval(() => {
      setStepIndex((i) => Math.min(i + 1, INVESTIGATION_STEPS.length - 1));
    }, 900);
    return () => clearInterval(interval);
  }, [loading]);

  const bundle = result?.evidence_bundle;
  const monthLabel = result?.target_month ? formatMonth(result.target_month) : "";

  const factors: { title: string; detail: string }[] = [];

  if (bundle?.largest_miss_category) {
    const categoryVariance = Number(bundle.largest_miss_variance_pct ?? 0);
    factors.push({
      title: categoryFactorTitle(bundle.largest_miss_category, categoryVariance),
      detail: categoryFactorDetail(categoryVariance),
    });
  }
  if (bundle?.largest_contributing_region) {
    factors.push({
      title: regionalFactorTitle(bundle.largest_contributing_region, "revenue_share"),
      detail: "Largest share of revenue in the period",
    });
  }
  if (bundle?.forecast_vs_target) {
    const fvt = bundle.forecast_vs_target;
    factors.push({
      title: `${fvt.category} forecast remained below target`,
      detail: `${formatCurrency(fvt.forecast_total)} forecast vs ${formatCurrency(fvt.target_total)} target`,
    });
  }
  if (bundle?.anomaly_signals && bundle.anomaly_signals.length > 0) {
    factors.push({
      title: `${bundle.anomaly_signals.length} unusual revenue signal${bundle.anomaly_signals.length > 1 ? "s" : ""} detected`,
      detail: "See evidence for details",
    });
  }

  return (
    <section className="card space-y-5">
      <div>
        <h2 className="font-display text-lg font-semibold">AI Investigation</h2>
        <p className="text-sm text-muted">
          Ask a business question — get an executive summary with evidence
        </p>
      </div>

      <div className="space-y-3">
        <textarea
          className="w-full rounded-xl border border-border bg-surface px-4 py-3 text-sm text-ink placeholder:text-muted focus:border-accent"
          rows={3}
          value={question}
          onChange={(e) => onQuestionChange(e.target.value)}
          placeholder="We missed the sales target by 12%. What factors contributed to the gap?"
          aria-label="Investigation question"
        />
        <button
          type="button"
          onClick={() => onRun(question.trim())}
          disabled={loading || question.trim().length < 5}
          className="btn-primary"
        >
          {loading ? "Analyzing…" : "Run investigation"}
        </button>
      </div>

      {error && (
        <p className="rounded-lg bg-negative-muted px-3 py-2 text-sm text-negative">
          {error}
        </p>
      )}

      {loading && (
        <LoadingPanel
          message="Analyzing target variance"
          steps={INVESTIGATION_STEPS.map((label, i) => ({
            label,
            done: i < stepIndex,
          }))}
        />
      )}

      {result && !loading && (
        <div className="animate-fade-in space-y-5 border-t border-border pt-5">
          <header className="space-y-2">
            <div className="rounded-lg border border-border bg-surface-elevated px-3 py-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted">
                Resolved period
              </p>
              <p className="font-display text-lg font-semibold text-ink">{monthLabel}</p>
              {result.month_resolution?.mode && (
                <p className="text-xs text-muted">
                  {formatResolutionMode(result.month_resolution.mode)}
                </p>
              )}
            </div>
            <h3 className="font-display text-xl font-semibold">
              {monthLabel} — Target {Number(bundle?.variance_pct ?? 0) < 0 ? "Miss" : "Summary"}
            </h3>
            <p className="text-sm text-muted">
              {formatCurrency(bundle?.target)} target → {formatCurrency(bundle?.actual)} actual
            </p>
            <p
              className={`font-display text-3xl font-bold ${
                Number(bundle?.variance_pct ?? 0) < 0 ? "metric-negative" : "metric-positive"
              }`}
            >
              {formatPercent(bundle?.variance_pct ?? 0)}
            </p>
          </header>

          {factors.length > 0 && (
            <div>
              <h4 className="mb-3 text-sm font-semibold text-ink">What happened?</h4>
              <ol className="space-y-2">
                {factors.map((f, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-3 rounded-lg border border-border bg-surface-elevated px-4 py-3"
                  >
                    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent-muted text-xs font-bold text-accent">
                      {i + 1}
                    </span>
                    <div>
                      <p className="text-sm font-medium text-ink">{f.title}</p>
                      <p className="text-xs text-muted">{f.detail}</p>
                    </div>
                  </li>
                ))}
              </ol>
            </div>
          )}

          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={onViewEvidence} className="btn-primary">
              View evidence
            </button>
            <button
              type="button"
              onClick={() => setShowTechnical(!showTechnical)}
              className="btn-ghost"
            >
              {showTechnical ? "Hide" : "Show"} technical report
            </button>
          </div>

          {result.report_provider === "deterministic_fallback" && (
            <p className="text-xs text-warning">
              LLM unavailable — showing deterministic fallback report.
            </p>
          )}

          {showTechnical && (
            <pre className="max-h-96 overflow-auto rounded-xl bg-panel p-4 text-xs leading-relaxed text-ink-secondary whitespace-pre-wrap">
              {result.report}
            </pre>
          )}
        </div>
      )}
    </section>
  );
}
