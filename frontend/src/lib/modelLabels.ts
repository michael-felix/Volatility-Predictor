const MODEL_LABELS: Record<string, string> = {
  har_rv: "HAR-RV",
  ridge: "Ridge Regression",
  random_forest: "Random Forest",
  xgboost: "XGBoost",
};

const MODEL_DESCRIPTIONS: Record<string, string> = {
  har_rv:
    "The classic econometric volatility model (Corsi's HAR-RV), purpose-built for this exact problem. Uses only three inputs — realized volatility over the last day, week, and month — rather than a large generic feature set.",
  ridge:
    "Linear regression with L2 regularization across every engineered feature. Included instead of plain linear regression, which it always matches or beats — regularization guards against overfitting with many correlated inputs.",
  random_forest:
    "An ensemble of many decision trees, each trained on a random subset of the data and features, averaged together. Captures nonlinear patterns plain regression can't.",
  xgboost:
    "Gradient-boosted decision trees: builds trees one at a time, each correcting the previous ones' errors, with strong built-in regularization. Included instead of a second, near-identical boosting implementation.",
};

/** Human-readable label for a backend algorithm identifier; falls back to
 * the raw identifier for any model added server-side that isn't listed here. */
export function modelLabel(algorithm: string): string {
  return MODEL_LABELS[algorithm] ?? algorithm;
}

/** One-line explanation of what an algorithm is and why it's in the
 * candidate set — addresses "why both X and Y, what's the difference". */
export function modelDescription(algorithm: string): string | null {
  return MODEL_DESCRIPTIONS[algorithm] ?? null;
}
