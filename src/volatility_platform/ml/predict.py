"""Inference: turn a trained model + latest engineered features into a
`VolatilityPrediction` domain object.

Deliberately thin. All feature computation happens in
`features/pipeline.py::build_feature_frame` (called here with
`include_target=False`) — this module never recomputes or approximates
a feature, which is what keeps it impossible for inference to silently
diverge from what the model was trained on.
"""

from __future__ import annotations

import pandas as pd
from sklearn.base import BaseEstimator

from volatility_platform.domain.models import ModelMetadata, Ticker, VolatilityPrediction


def predict_volatility(
    model: BaseEstimator,
    metadata: ModelMetadata,
    feature_frame: pd.DataFrame,
    ticker: Ticker,
    current_price: float,
) -> VolatilityPrediction:
    """Predict volatility from the most recent row of `feature_frame`.

    `feature_frame` must be built via `build_feature_frame(...,
    include_target=False)` over the same OHLCV history the model was
    trained on. Columns are selected and ordered by `metadata.feature_names`
    so column order in `feature_frame` can never silently misalign with
    what the model expects.
    """
    latest_row = feature_frame.iloc[[-1]][list(metadata.feature_names)]
    raw_prediction = float(model.predict(latest_row)[0])

    # Volatility cannot be negative; a linear model can still emit a
    # small negative value near zero, which we clip rather than propagate.
    predicted_volatility = max(raw_prediction, 0.0)

    as_of_index = feature_frame.index[-1]
    as_of_date = as_of_index.date() if isinstance(as_of_index, pd.Timestamp) else as_of_index

    return VolatilityPrediction(
        ticker=ticker,
        horizon_days=metadata.horizon_days,
        predicted_volatility=predicted_volatility,
        current_price=current_price,
        model_name=metadata.name,
        model_version=metadata.version,
        as_of_date=as_of_date,
    )
