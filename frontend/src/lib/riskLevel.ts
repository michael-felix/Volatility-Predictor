/**
 * Plain-language risk classification from annualized volatility percentage.
 *
 * Thresholds are illustrative, not a rigorous statistical standard: broad
 * market indices (S&P 500) have historically averaged ~15-20% annualized
 * volatility, and individual stocks typically run higher. These bands give
 * a retail-friendly "is this calm or turbulent" read rather than a precise
 * percentile — see the /guide page for the caveat.
 */

export type RiskLevel = "low" | "medium" | "high";

export function getRiskLevel(annualizedVolatilityPct: number): RiskLevel {
  if (annualizedVolatilityPct < 15) return "low";
  if (annualizedVolatilityPct < 30) return "medium";
  return "high";
}

export const RISK_CONFIG: Record<RiskLevel, { label: string; color: string }> = {
  low: { label: "Low risk", color: "var(--status-good)" },
  medium: { label: "Medium risk", color: "var(--status-warning)" },
  high: { label: "High risk", color: "var(--status-critical)" },
};
