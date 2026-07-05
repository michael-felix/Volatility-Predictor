"""Model training: cross-validated candidate selection, then a final refit.

Training is intentionally separate from inference (`predict.py`):
training consumes labeled historical data and runs offline (a scheduled
job or manual CLI invocation, see `pipelines/train_model.py`), while
inference runs synchronously inside an API request and must be fast and
side-effect-free beyond producing a single prediction.

Candidate models are deliberately four *different* approaches rather
than a longer list of near-duplicates:

- **HAR-RV**: the classic econometric volatility model (Corsi 2009) —
  plain linear regression using only the three HAR realized-volatility
  features (daily/weekly/monthly), nothing else. This is the standard
  domain-specific baseline for volatility forecasting specifically,
  not a generic ML model bolted onto the problem.
- **Ridge**: linear regression with L2 regularization over the *full*
  engineered feature set. Included instead of plain (unregularized)
  linear regression — Ridge subsumes it (alpha -> 0 recovers OLS) and
  is safer with many correlated engineered features relative to the
  sample size.
- **Random Forest**: a bagged ensemble of decision trees — a different
  bias/variance tradeoff from either linear model, and from boosting.
- **XGBoost**: regularized gradient-boosted trees. Included instead of
  scikit-learn's plain `GradientBoostingRegressor` — the two are close
  to the same underlying algorithm, and XGBoost's built-in
  regularization tends to generalize better on small datasets like
  this one's per-training-run sample size.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
from sklearn.base import BaseEstimator, clone
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge
from xgboost import XGBRegressor

from volatility_platform.domain.exceptions import InsufficientDataError
from volatility_platform.domain.models import ModelMetadata
from volatility_platform.ml.evaluation import time_series_cv_scores

RANDOM_STATE = 42

# Below this many rows, time-series CV folds get too small (and too few)
# to produce a meaningful model comparison.
MIN_TRAINING_ROWS = 60

# The three features Corsi's HAR-RV model uses — see features/volatility.py::har_features.
HAR_FEATURE_COLUMNS = ("rv_daily", "rv_weekly", "rv_monthly")

CANDIDATE_MODELS: dict[str, BaseEstimator] = {
    "har_rv": LinearRegression(),
    "ridge": Ridge(alpha=1.0, random_state=RANDOM_STATE),
    "random_forest": RandomForestRegressor(
        n_estimators=200, max_depth=6, random_state=RANDOM_STATE
    ),
    "xgboost": XGBRegressor(n_estimators=200, max_depth=3, random_state=RANDOM_STATE, n_jobs=1),
}

# Candidates not listed here train on every engineered feature column.
CANDIDATE_FEATURE_COLUMNS: dict[str, tuple[str, ...]] = {
    "har_rv": HAR_FEATURE_COLUMNS,
}


def _feature_subset(features: pd.DataFrame, candidate_name: str) -> pd.DataFrame:
    columns = CANDIDATE_FEATURE_COLUMNS.get(candidate_name)
    return features[list(columns)] if columns else features


def select_best_model(
    feature_frame: pd.DataFrame, n_splits: int = 5
) -> tuple[str, dict[str, dict[str, float]]]:
    """Cross-validate every candidate and return the best name (lowest CV RMSE)
    plus every candidate's CV metrics, so the losing candidates' scores are
    still visible for logging/debugging rather than silently discarded."""
    if len(feature_frame) < MIN_TRAINING_ROWS:
        raise InsufficientDataError(
            f"Need at least {MIN_TRAINING_ROWS} rows to train, got {len(feature_frame)}"
        )

    features = feature_frame.drop(columns=["target"])
    target = feature_frame["target"]

    all_scores = {
        name: time_series_cv_scores(
            model, _feature_subset(features, name), target, n_splits=n_splits
        )
        for name, model in CANDIDATE_MODELS.items()
    }
    best_name = min(all_scores, key=lambda name: all_scores[name]["rmse"])
    return best_name, all_scores


def train_model(
    feature_frame: pd.DataFrame,
    model_name: str,
    horizon_days: int,
    n_splits: int = 5,
) -> tuple[BaseEstimator, ModelMetadata]:
    """Select the best candidate via CV, refit it on the full dataset, and
    package it with `ModelMetadata` ready for `registry.save_model`.

    The CV metrics attached to the metadata come from held-out folds
    during model selection — not from scoring the final refit against
    its own training data, which would be optimistic and misleading.
    """
    best_candidate_name, all_scores = select_best_model(feature_frame, n_splits=n_splits)

    features = feature_frame.drop(columns=["target"])
    target = feature_frame["target"]
    best_features = _feature_subset(features, best_candidate_name)

    estimator = clone(CANDIDATE_MODELS[best_candidate_name])
    estimator.fit(best_features, target)

    trained_at = datetime.now(UTC)
    metadata = ModelMetadata(
        name=model_name,
        version=trained_at.strftime("%Y%m%d_%H%M%S"),
        algorithm=best_candidate_name,
        horizon_days=horizon_days,
        trained_at=trained_at,
        feature_names=tuple(best_features.columns),
        metrics=all_scores[best_candidate_name],
        hyperparameters=estimator.get_params(),
        training_samples=len(feature_frame),
        candidate_metrics=all_scores,
    )
    return estimator, metadata
