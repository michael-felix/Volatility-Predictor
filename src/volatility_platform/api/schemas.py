"""Pydantic request/response models — the API's boundary contracts.

Kept deliberately separate from `domain.models`: domain objects are
framework-free dataclasses used throughout services/ML code, while these
schemas own request validation and JSON response shape. Conversion
between the two happens in one direction each way, via the `from_domain`
classmethods below — never inline in a router function.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Self

from pydantic import BaseModel, Field

from volatility_platform.domain.models import ModelMetadata, VolatilityPrediction


class PredictionRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=10, examples=["AAPL"])
    model_name: str | None = Field(
        default=None, description="Defaults to the configured model name"
    )


class PredictionResponse(BaseModel):
    ticker: str
    horizon_days: int
    as_of_date: date
    current_price: float
    predicted_volatility: float
    annualized_volatility_pct: float
    expected_move_pct: float
    expected_move_dollars: float
    expected_price_range_low: float
    expected_price_range_high: float
    model_name: str
    model_version: str
    generated_at: datetime

    @classmethod
    def from_domain(cls, prediction: VolatilityPrediction) -> PredictionResponse:
        low, high = prediction.expected_price_range
        return cls(
            ticker=prediction.ticker.symbol,
            horizon_days=prediction.horizon_days,
            as_of_date=prediction.as_of_date,
            current_price=prediction.current_price,
            predicted_volatility=prediction.predicted_volatility,
            annualized_volatility_pct=prediction.annualized_volatility_pct,
            expected_move_pct=prediction.expected_move_pct,
            expected_move_dollars=prediction.expected_move_dollars,
            expected_price_range_low=low,
            expected_price_range_high=high,
            model_name=prediction.model_name,
            model_version=prediction.model_version,
            generated_at=prediction.generated_at,
        )


class TrainRequest(BaseModel):
    tickers: list[str] | None = Field(
        default=None, description="Defaults to the configured default tickers"
    )
    horizon_days: int = Field(default=5, gt=0, le=30)


class TrainResponse(BaseModel):
    model_name: str
    version: str
    algorithm: str
    horizon_days: int
    trained_at: datetime
    training_samples: int
    metrics: dict[str, float]
    feature_names: list[str]
    candidate_metrics: dict[str, dict[str, float]] = Field(
        default_factory=dict,
        description="Every candidate model's CV metrics from the training run that "
        "produced this model, keyed by algorithm name — powers the model comparison page.",
    )

    @classmethod
    def from_domain(cls, metadata: ModelMetadata) -> Self:
        return cls(
            model_name=metadata.name,
            version=metadata.version,
            algorithm=metadata.algorithm,
            horizon_days=metadata.horizon_days,
            trained_at=metadata.trained_at,
            training_samples=metadata.training_samples,
            metrics=metadata.metrics,
            feature_names=list(metadata.feature_names),
            candidate_metrics=metadata.candidate_metrics,
        )


class ModelInfoResponse(TrainResponse):
    """Same shape as `TrainResponse` — describes whichever model version is currently active."""


class TickerInfo(BaseModel):
    ticker: str
    latest_trading_date: date | None
    bar_count: int


class HealthResponse(BaseModel):
    status: str
    mongodb_connected: bool
