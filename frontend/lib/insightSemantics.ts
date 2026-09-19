/** Sign-aware copy for executive insights and investigation factors. */

export type RegionalMetric = "revenue_share" | "variance_contribution" | "achievement";

export function isNegativeVariance(variancePct: number): boolean {
  return variancePct < 0;
}

export function categoryInsightHeadline(category: string, variancePct: number): string {
  if (isNegativeVariance(variancePct)) {
    return `${category} is the biggest target miss`;
  }
  return `${category} was the largest positive contributor to target overperformance`;
}

export function categoryInsightExplanation(
  category: string,
  variancePct: number,
  month: string,
): string {
  if (isNegativeVariance(variancePct)) {
    return `${category} finished ${Math.abs(variancePct).toFixed(1)}% below target in ${month}.`;
  }
  return `${category} exceeded its target by ${variancePct.toFixed(1)}% in ${month}.`;
}

export function categoryFactorTitle(category: string, variancePct: number): string {
  if (isNegativeVariance(variancePct)) {
    return `${category} drove the largest category shortfall`;
  }
  return `${category} was the largest positive contributor to target overperformance`;
}

export function categoryFactorDetail(variancePct: number): string {
  if (isNegativeVariance(variancePct)) {
    return `${variancePct.toFixed(2)}% vs target`;
  }
  return `+${variancePct.toFixed(2)}% above target`;
}

export function regionalFactorTitle(region: string, metric: RegionalMetric): string {
  switch (metric) {
    case "revenue_share":
      return `${region} had the largest share of revenue`;
    case "variance_contribution":
      return `${region} was the largest contribution to target variance`;
    case "achievement":
      return `${region} had the highest target achievement`;
  }
}

export function chartCategoryHighlightLabel(variancePct: number): string {
  return isNegativeVariance(variancePct)
    ? "Largest miss"
    : "Largest positive contributor";
}
