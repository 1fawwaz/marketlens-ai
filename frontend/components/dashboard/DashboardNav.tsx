import type { NavSection } from "@/lib/types";

const NAV_ITEMS: { id: NavSection; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "target", label: "Target Analysis" },
  { id: "forecasts", label: "Forecasts" },
  { id: "anomalies", label: "Anomalies" },
  { id: "investigations", label: "Investigations" },
];

type DashboardNavProps = {
  active: NavSection;
  onChange: (section: NavSection) => void;
};

export function DashboardNav({ active, onChange }: DashboardNavProps) {
  return (
    <nav className="flex gap-1 overflow-x-auto border-b border-border pb-px" aria-label="Dashboard">
      {NAV_ITEMS.map((item) => (
        <button
          key={item.id}
          type="button"
          onClick={() => onChange(item.id)}
          className={`nav-tab shrink-0 whitespace-nowrap ${
            active === item.id ? "nav-tab-active" : ""
          }`}
        >
          {item.label}
        </button>
      ))}
    </nav>
  );
}
