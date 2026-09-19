export function formatCurrency(value: number | null | undefined, compact = true): string {
  if (value == null || Number.isNaN(value)) return "—";
  if (compact) {
    const abs = Math.abs(value);
    if (abs >= 1_000_000) return `₹${(value / 1_000_000).toFixed(1)}M`;
    if (abs >= 1_000) return `₹${(value / 1_000).toFixed(1)}K`;
  }
  return `₹${value.toLocaleString("en-IN", { maximumFractionDigits: 1 })}`;
}

export function formatPercent(value: number | null | undefined, signed = true): string {
  if (value == null || Number.isNaN(value)) return "—";
  const prefix = signed && value > 0 ? "+" : "";
  return `${prefix}${value.toFixed(2)}%`;
}

export function formatPercentCompact(value: number | null | undefined, signed = true): string {
  if (value == null || Number.isNaN(value)) return "—";
  const prefix = signed && value > 0 ? "+" : "";
  return `${prefix}${value.toFixed(1)}%`;
}

export function formatMonth(isoDate: string): string {
  const d = new Date(isoDate);
  if (Number.isNaN(d.getTime())) return isoDate;
  return d.toLocaleDateString("en-IN", { month: "short", year: "numeric" });
}

export function formatShortDate(isoDate: string): string {
  const d = new Date(isoDate);
  if (Number.isNaN(d.getTime())) return isoDate;
  return d.toLocaleDateString("en-IN", { month: "short", day: "numeric" });
}

export function monthKey(isoDate: string): string {
  return String(isoDate).slice(0, 7);
}

export function isNegativeMetric(value: number): boolean {
  return value < 0;
}

export function formatResolutionMode(mode: string): string {
  switch (mode) {
    case "explicit_date":
      return "Explicit date in question";
    case "percent_match":
      return "Matched from variance %";
    case "auto_worst_month":
      return "Worst month in dataset";
    case "dashboard_context":
      return "Dashboard selected period";
    case "latest_available":
      return "Latest available period";
    default:
      return mode.replace(/_/g, " ");
  }
}
