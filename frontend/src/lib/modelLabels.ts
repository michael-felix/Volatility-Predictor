const MODEL_LABELS: Record<string, string> = {
  linear_regression: "Linear Regression",
  ridge: "Ridge Regression",
  random_forest: "Random Forest",
  gradient_boosting: "Gradient Boosting",
  xgboost: "XGBoost",
};

/** Human-readable label for a backend algorithm identifier; falls back to
 * the raw identifier for any model added server-side that isn't listed here. */
export function modelLabel(algorithm: string): string {
  return MODEL_LABELS[algorithm] ?? algorithm;
}
