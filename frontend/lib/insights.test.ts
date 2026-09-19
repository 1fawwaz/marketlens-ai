import { describe, expect, it } from "vitest";
import { aggregateMonthlyChart, buildExecutiveInsights } from "./insights";
import type { VarianceRow } from "./types";

const march2019Rows: VarianceRow[] = [
  {
    snapshot_id: 1,
    target_month: "2019-03-01",
    category: "Electronics",
    target_amount: 20000,
    actual_amount: 26000,
    variance_amount: 6000,
    variance_pct: 30.0,
    top_state: "Maharashtra",
    top_state_amount: 12000,
  },
  {
    snapshot_id: 2,
    target_month: "2019-03-01",
    category: "Clothing",
    target_amount: 23800,
    actual_amount: 32900,
    variance_amount: 9100,
    variance_pct: 38.2,
    top_state: "Delhi",
    top_state_amount: 15000,
  },
];

const july2018Miss: VarianceRow[] = [
  {
    snapshot_id: 3,
    target_month: "2018-07-01",
    category: "Clothing",
    target_amount: 16000,
    actual_amount: 3400,
    variance_amount: -12600,
    variance_pct: -78.7,
    top_state: "Karnataka",
    top_state_amount: 2000,
  },
];

describe("buildExecutiveInsights", () => {
  it("surfaces overperformance insights for positive variance periods", () => {
    const insights = buildExecutiveInsights(march2019Rows, [], [], "Clothing", 0);
    expect(insights.length).toBeGreaterThan(0);
    expect(insights[0].type).toBe("OPPORTUNITY");
    expect(insights[0].headline).toContain("positive contributor");
    expect(insights[0].headline.toLowerCase()).not.toContain("shortfall");
    expect(insights[0].metricValue).toBeGreaterThan(0);
  });

  it("surfaces target miss insights for negative variance periods", () => {
    const insights = buildExecutiveInsights(july2018Miss, [], [], "Clothing", 0);
    expect(insights[0].type).toBe("TARGET MISS");
    expect(insights[0].headline).toContain("biggest target miss");
    expect(insights[0].metricValue).toBeLessThan(0);
  });
});

describe("aggregateMonthlyChart", () => {
  it("labels positive category highlights without miss wording", () => {
    const { summary } = aggregateMonthlyChart(march2019Rows);
    expect(summary.categoryHighlightLabel).toBe("Largest positive contributor");
    expect(summary.categoryHighlightVariancePct).toBeGreaterThan(0);
  });

  it("labels negative category highlights as largest miss", () => {
    const { summary } = aggregateMonthlyChart(july2018Miss);
    expect(summary.categoryHighlightLabel).toBe("Largest miss");
    expect(summary.categoryHighlightVariancePct).toBeLessThan(0);
  });
});
