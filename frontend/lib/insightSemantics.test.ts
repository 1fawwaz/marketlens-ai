import { describe, expect, it } from "vitest";
import {
  categoryFactorDetail,
  categoryFactorTitle,
  categoryInsightExplanation,
  categoryInsightHeadline,
  chartCategoryHighlightLabel,
  regionalFactorTitle,
} from "./insightSemantics";

describe("category insight semantics", () => {
  it("uses shortfall wording for negative variance", () => {
    expect(categoryInsightHeadline("Clothing", -78.7)).toBe(
      "Clothing is the biggest target miss",
    );
    expect(categoryFactorTitle("Clothing", -78.7)).toBe(
      "Clothing drove the largest category shortfall",
    );
    expect(categoryInsightExplanation("Clothing", -78.7, "Jul 2018")).toBe(
      "Clothing finished 78.7% below target in Jul 2018.",
    );
    expect(categoryFactorDetail(-40.2)).toBe("-40.20% vs target");
  });

  it("uses overperformance wording for positive variance", () => {
    expect(categoryInsightHeadline("Electronics", 30.38)).toBe(
      "Electronics was the largest positive contributor to target overperformance",
    );
    expect(categoryFactorTitle("Electronics", 30.38)).toBe(
      "Electronics was the largest positive contributor to target overperformance",
    );
    expect(categoryInsightExplanation("Electronics", 30.38, "Mar 2019")).toBe(
      "Electronics exceeded its target by 30.4% in Mar 2019.",
    );
    expect(categoryFactorDetail(30.38)).toBe("+30.38% above target");
  });

  it("does not label positive variance as a shortfall", () => {
    const headline = categoryFactorTitle("Electronics", 30.38);
    expect(headline.toLowerCase()).not.toContain("shortfall");
    expect(headline.toLowerCase()).not.toContain("miss");
  });
});

describe("regional factor semantics", () => {
  it("uses metric-specific regional wording", () => {
    expect(regionalFactorTitle("Delhi", "revenue_share")).toBe(
      "Delhi had the largest share of revenue",
    );
    expect(regionalFactorTitle("Delhi", "variance_contribution")).toBe(
      "Delhi was the largest contribution to target variance",
    );
    expect(regionalFactorTitle("Delhi", "achievement")).toBe(
      "Delhi had the highest target achievement",
    );
  });
});

describe("chart summary semantics", () => {
  it("labels positive category highlights correctly", () => {
    expect(chartCategoryHighlightLabel(34.56)).toBe("Largest positive contributor");
    expect(chartCategoryHighlightLabel(-12.4)).toBe("Largest miss");
  });
});
