"""Model training: cross-validated candidate selection, then a final refit.

Training is intentionally separate from inference (`predict.py`):
training consumes labeled historical data and runs offline (a scheduled
job or manual CLI invocation, see `pipelines/train_model.py`), while
inference runs synchronously inside an API request and must be fast and
side-effect-free beyond producing a single prediction.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
from sklearn.base import BaseEstimator, clone
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression

from volatility_platform.domain.exceptions import InsufficientDataError
from volatility_platform.domain.models import ModelMetadata
from volatility_platform.ml.evaluation import time_series_cv_scores

RANDOM_STATE = 42

# Below this many rows, time-series CV folds get too small (and too few)
# to produce a meaningful model comparison.
MIN_TRAINING_ROWS = 60

CANDIDATE_MODELS: dict[str, BaseEstimator] = {
    "linear_regression": LinearRegression(),
    "random_forest": RandomForestRegressor(
        n_estimators=200, max_depth=6, random_state=RANDOM_STATE
    ),
    "gradient_boosting": GradientBoostingRegressor(
        n_estimators=200, max_depth=3, random_state=RANDOM_STATE
    ),
}


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
        name: time_series_cv_scores(model, features, target, n_splits=n_splits)
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

    estimator = clone(CANDIDATE_MODELS[best_candidate_name])
    estimator.fit(features, target)

    trained_at = datetime.now(UTC)
    metadata = ModelMetadata(
        name=model_name,
        version=trained_at.strftime("%Y%m%d_%H%M%S"),
        algorithm=best_candidate_name,
        horizon_days=horizon_days,
        trained_at=trained_at,
        feature_names=tuple(features.columns),
        metrics=all_scores[best_candidate_name],
        hyperparameters=estimator.get_params(),
        training_samples=len(feature_frame),
    )
    return estimator, metadata
