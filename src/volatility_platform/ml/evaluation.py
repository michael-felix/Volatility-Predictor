"""Evaluation metrics and time-series-aware cross-validation.

Cross-validation uses `TimeSeriesSplit` rather than a shuffled k-fold:
shuffled folds would let a model train on future rows to predict past
ones, which is lookahead bias at the model-selection level, layered on
top of the leakage already guarded against inside the feature pipeline
(`features/pipeline.py`). Every fold here trains on an earlier
contiguous block and validates on a strictly later one.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, clone
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import TimeSeriesSplit

from volatility_platform.domain.exceptions import InsufficientDataError


def regression_metrics(y_true: pd.Series, y_pred: np.ndarray) -> dict[str, float]:
    """Compute RMSE, MAE, and R^2 for a set of predictions."""
    return {
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "r2": float(r2_score(y_true, y_pred)),
    }


def time_series_cv_scores(
    model: BaseEstimator, features: pd.DataFrame, target: pd.Series, n_splits: int = 5
) -> dict[str, float]:
    """Cross-validate `model` using expanding-window time-series splits.

    Returns each metric averaged across folds. `features`/`target` must
    already be sorted chronologically (guaranteed by
    `build_feature_frame`'s date-sorted index).
    """
    if len(features) <= n_splits:
        raise InsufficientDataError(
            f"Need more than {n_splits} rows for {n_splits}-fold CV, got {len(features)}"
        )

    splitter = TimeSeriesSplit(n_splits=n_splits)
    fold_metrics: list[dict[str, float]] = []

    for train_idx, val_idx in splitter.split(features):
        fold_model = clone(model)
        fold_model.fit(features.iloc[train_idx], target.iloc[train_idx])
        predictions = fold_model.predict(features.iloc[val_idx])
        fold_metrics.append(regression_metrics(target.iloc[val_idx], predictions))

    return {key: float(np.mean([fold[key] for fold in fold_metrics])) for key in fold_metrics[0]}
