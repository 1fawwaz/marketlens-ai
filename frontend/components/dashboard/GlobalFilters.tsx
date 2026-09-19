import type { DashboardFilters } from "@/lib/types";

type GlobalFiltersProps = {
  filters: DashboardFilters;
  months: string[];
  categories: string[];
  states: string[];
  onChange: (filters: DashboardFilters) => void;
};

export function GlobalFilters({
  filters,
  months,
  categories,
  states,
  onChange,
}: GlobalFiltersProps) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <select
        className="filter-select"
        value={filters.month}
        onChange={(e) => onChange({ ...filters, month: e.target.value })}
        aria-label="Filter by month"
      >
        <option value="">All months</option>
        {months.map((m) => (
          <option key={m} value={m}>{m}</option>
        ))}
      </select>

      <select
        className="filter-select"
        value={filters.category}
        onChange={(e) => onChange({ ...filters, category: e.target.value })}
        aria-label="Filter by category"
      >
        <option value="">All categories</option>
        {categories.map((c) => (
          <option key={c} value={c}>{c}</option>
        ))}
      </select>

      <select
        className="filter-select"
        value={filters.state}
        onChange={(e) => onChange({ ...filters, state: e.target.value })}
        aria-label="Filter by state"
      >
        <option value="">All states</option>
        {states.map((s) => (
          <option key={s} value={s}>{s}</option>
        ))}
      </select>

      <select
        className="filter-select"
        value={filters.metric}
        onChange={(e) =>
          onChange({ ...filters, metric: e.target.value as DashboardFilters["metric"] })
        }
        aria-label="Filter by metric"
      >
        <option value="revenue">Revenue</option>
        <option value="variance">Variance</option>
      </select>
    </div>
  );
}
