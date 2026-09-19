import type { ReactNode } from "react";

type LoadingPanelProps = {
  message?: string;
  steps?: { label: string; done: boolean }[];
};

export function LoadingPanel({ message = "Loading…", steps }: LoadingPanelProps) {
  return (
    <div className="card flex flex-col items-center justify-center py-12 text-center">
      <div className="mb-4 h-8 w-8 animate-spin rounded-full border-2 border-accent border-t-transparent" />
      <p className="text-sm font-medium text-ink">{message}</p>
      {steps && (
        <ul className="mt-4 space-y-1 text-left text-xs text-muted">
          {steps.map((s) => (
            <li key={s.label} className="flex items-center gap-2">
              <span className={s.done ? "text-positive" : "text-accent"}>
                {s.done ? "✓" : "●"}
              </span>
              {s.label}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function EmptyPanel({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="card flex flex-col items-center justify-center py-12 text-center">
      <p className="font-display text-base font-semibold">{title}</p>
      <p className="mt-1 max-w-sm text-sm text-muted">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorPanel({
  title = "Something went wrong",
  message,
  onRetry,
}: {
  title?: string;
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="rounded-xl border border-negative/30 bg-negative-muted p-4">
      <p className="font-medium text-negative">{title}</p>
      <p className="mt-1 text-sm text-ink-secondary">{message}</p>
      {onRetry && (
        <button type="button" onClick={onRetry} className="btn-primary mt-3">
          Retry
        </button>
      )}
    </div>
  );
}
