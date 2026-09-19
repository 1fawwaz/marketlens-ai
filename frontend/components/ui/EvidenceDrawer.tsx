"use client";

import type { ExecutiveInsight, InvestigationResult, ToolResult } from "@/lib/types";

type EvidenceDrawerProps = {
  open: boolean;
  onClose: () => void;
  insight?: ExecutiveInsight | null;
  investigation?: InvestigationResult | null;
};

function JsonBlock({ data }: { data: unknown }) {
  return (
    <pre className="max-h-48 overflow-auto rounded-lg bg-panel p-3 text-[11px] leading-relaxed text-ink-secondary">
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}

export function EvidenceDrawer({
  open,
  onClose,
  insight,
  investigation,
}: EvidenceDrawerProps) {
  if (!open) return null;

  const bundle = investigation?.evidence_bundle;
  const toolResults = investigation?.tool_results ?? [];

  return (
    <>
      <div
        className="fixed inset-0 z-40 bg-ink/40 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden
      />
      <aside
        className="fixed right-0 top-0 z-50 flex h-full w-full max-w-md flex-col border-l border-border bg-surface shadow-elevated animate-slide-up"
        role="dialog"
        aria-label="Evidence details"
      >
        <header className="flex items-center justify-between border-b border-border px-5 py-4">
          <div>
            <h2 className="font-display text-base font-semibold">Evidence</h2>
            <p className="text-xs text-muted">Provenance and supporting data</p>
          </div>
          <button type="button" onClick={onClose} className="btn-ghost" aria-label="Close">
            ✕
          </button>
        </header>

        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          {insight && (
            <section className="space-y-2">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-muted">
                Insight evidence
              </h3>
              <dl className="space-y-2 text-sm">
                <div>
                  <dt className="text-muted">Evidence ID</dt>
                  <dd className="font-mono text-xs">{insight.evidenceId}</dd>
                </div>
                <div>
                  <dt className="text-muted">Source tool</dt>
                  <dd>{insight.evidenceTool}</dd>
                </div>
                <div>
                  <dt className="text-muted">Supporting numbers</dt>
                  <dd>{insight.explanation}</dd>
                </div>
              </dl>
              {insight.evidenceDetails && (
                <JsonBlock data={insight.evidenceDetails} />
              )}
            </section>
          )}

          {bundle && (
            <section className="space-y-2">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-muted">
                Investigation bundle
              </h3>
              <dl className="grid grid-cols-2 gap-2 text-sm">
                {bundle.target != null && (
                  <div>
                    <dt className="text-muted">Target</dt>
                    <dd>₹{bundle.target.toLocaleString()}</dd>
                  </div>
                )}
                {bundle.actual != null && (
                  <div>
                    <dt className="text-muted">Actual</dt>
                    <dd>₹{bundle.actual.toLocaleString()}</dd>
                  </div>
                )}
                {bundle.variance_pct != null && (
                  <div>
                    <dt className="text-muted">Variance</dt>
                    <dd>{bundle.variance_pct}%</dd>
                  </div>
                )}
              </dl>
              {bundle.supporting_query_ids && bundle.supporting_query_ids.length > 0 && (
                <div>
                  <p className="mb-1 text-xs text-muted">Query IDs</p>
                  <ul className="space-y-1">
                    {bundle.supporting_query_ids.map((id) => (
                      <li key={id} className="font-mono text-[11px] text-ink-secondary">
                        {id}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {bundle.notes && (
                <ul className="list-disc pl-4 text-xs text-muted">
                  {bundle.notes.map((n) => (
                    <li key={n}>{n}</li>
                  ))}
                </ul>
              )}
            </section>
          )}

          {toolResults.length > 0 && (
            <section className="space-y-3">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-muted">
                Tool results
              </h3>
              {toolResults.map((tr: ToolResult, i) => (
                <div key={i} className="rounded-lg border border-border p-3">
                  <p className="text-sm font-medium">
                    {tr.tool}
                    {tr.template ? ` • ${tr.template}` : ""}
                  </p>
                  <p className="mt-0.5 font-mono text-[10px] text-muted">
                    {tr.payload?.provenance?.query_id ?? tr.payload?.query_id ?? "—"}
                  </p>
                  <div className="mt-2">
                    <JsonBlock data={tr.payload} />
                  </div>
                </div>
              ))}
            </section>
          )}

          {!insight && !bundle && toolResults.length === 0 && (
            <p className="text-sm text-muted">No evidence selected.</p>
          )}

          <section className="rounded-lg bg-accent-muted/50 p-3 text-xs text-muted">
            <strong className="text-ink-secondary">Limitations:</strong> Anomaly flags
            indicate statistical outliers, not proven causes. Festival dates are contextual
            associations only.
          </section>
        </div>
      </aside>
    </>
  );
}
