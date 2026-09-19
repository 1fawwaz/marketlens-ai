"use client";

import type { SystemStatus } from "@/lib/types";

type DashboardHeaderProps = {
  selectedMonth: string;
  months: string[];
  onMonthChange: (month: string) => void;
  onRefresh: () => void;
  loading: boolean;
  status: SystemStatus | null;
  darkMode: boolean;
  onToggleTheme: () => void;
  onLogout: () => void;
};

export function DashboardHeader({
  selectedMonth,
  months,
  onMonthChange,
  onRefresh,
  loading,
  status,
  darkMode,
  onToggleTheme,
  onLogout,
}: DashboardHeaderProps) {
  const connected = status != null;
  const llmAvailable = status?.llm?.available ?? false;

  return (
    <header className="flex flex-col gap-4 border-b border-border pb-5 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h1 className="font-display text-xl font-semibold tracking-tight text-ink sm:text-2xl">
          MarketLens AI
        </h1>
        <p className="text-sm text-muted">AI-powered target variance intelligence</p>
      </div>

      <div className="flex flex-wrap items-center gap-2 sm:gap-3">
        <select
          className="filter-select"
          value={selectedMonth}
          onChange={(e) => onMonthChange(e.target.value)}
          aria-label="Select period"
        >
          <option value="">All periods</option>
          {months.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>

        <button
          type="button"
          onClick={onRefresh}
          disabled={loading}
          className="btn-ghost"
          aria-label="Refresh data"
        >
          {loading ? "Refreshing…" : "↻ Refresh"}
        </button>

        <button
          type="button"
          onClick={onToggleTheme}
          className="btn-ghost"
          aria-label="Toggle theme"
        >
          {darkMode ? "☀" : "☾"}
        </button>

        <div
          className="flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-1.5"
          title={connected ? "Backend connected" : "Backend unavailable"}
        >
          <span
            className={`h-2 w-2 rounded-full ${
              connected ? "bg-positive" : "bg-negative"
            }`}
          />
          <span className="text-xs text-muted">
            {connected ? (llmAvailable ? "AI ready" : "Connected") : "Offline"}
          </span>
        </div>

        <button type="button" onClick={onLogout} className="btn-ghost text-xs">
          Sign out
        </button>
      </div>
    </header>
  );
}
