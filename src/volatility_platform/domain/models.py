"""Core domain models.

These are plain, framework-free dataclasses: no pandas, no MongoDB, no
FastAPI. They represent *what the business objects are*, independent of
how they're stored (Mongo documents) or transmitted (API JSON). Adapters
in `repositories/` and `api/schemas.py` convert to/from these types.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from volatility_platform.domain.exceptions import DataValidationError

_TICKER_PATTERN = re.compile(r"^[A-Z]{1,10}([.-][A-Z]{1,4})?$")

# Shared with features/volatility.py, which imports this constant rather than
# redefining it — annualization must use one number, not two copies that could drift.
TRADING_DAYS_PER_YEAR = 252


@dataclass(frozen=True, slots=True)
class Ticker:
    """A validated stock ticker symbol, e.g. 'AAPL', 'BRK.B'."""

    symbol: str

    def __post_init__(self) -> None:
        normalized = self.symbol.strip().upper()
        if not _TICKER_PATTERN.match(normalized):
            raise DataValidationError(f"Invalid ticker symbol: {self.symbol!r}")
        object.__setattr__(self, "symbol", normalized)

    def __str__(self) -> str:
        return self.symbol


@dataclass(frozen=True, slots=True)
class OHLCVBar:
    """A single day's Open/High/Low/Close/Volume bar for a ticker."""

    ticker: Ticker
    trading_date: date
    open: float
    high: float
    low: float
    close: float
    volume: int

    def __post_init__(self) -> None:
        if self.high < self.low:
            raise DataValidationError(
                f"{self.ticker} {self.trading_date}: high ({self.high}) < low ({self.low})"
            )
        prices = (self.open, self.high, self.low, self.close)
        if any(p <= 0 for p in prices):
            raise DataValidationError(
                f"{self.ticker} {self.trading_date}: prices must be positive, got {prices}"
            )
        if not (self.low <= self.open <= self.high):
            raise DataValidationError(
                f"{self.ticker} {self.trading_date}: open ({self.open}) outside "
                f"[low={self.low}, high={self.high}]"
            )
        if not (self.low <= self.close <= self.high):
            raise DataValidationError(
                f"{self.ticker} {self.trading_date}: close ({self.close}) outside "
                f"[low={self.low}, high={self.high}]"
            )
        if self.volume < 0:
            raise DataValidationError(f"{self.ticker} {self.trading_date}: negative volume")


@dataclass(frozen=True, slots=True)
class VolatilityPrediction:
    """A model's volatility forecast for a ticker over a given horizon.

    `predicted_volatility` is the raw model output: realized volatility
    over the *entire* `horizon_days` period, on the same daily-log-return
    scale the model was trained on (see `features/pipeline.py::compute_target`).
    That raw scale is what keeps training numerically well-behaved, but it
    isn't what a dashboard should show a human — the properties below
    derive the industry-standard annualized percentage and a concrete
    expected dollar move, computed once here so the API and frontend never
    have to re-derive (and potentially mis-derive) them independently.
    """

    ticker: Ticker
    horizon_days: int
    predicted_volatility: float
    current_price: float
    model_name: str
    model_version: str
    as_of_date: date
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if self.horizon_days <= 0:
            raise DataValidationError("horizon_days must be positive")
        if self.predicted_volatility < 0:
            raise DataValidationError("predicted_volatility cannot be negative")
        if self.current_price <= 0:
            raise DataValidationError("current_price must be positive")

    @property
    def annualized_volatility_pct(self) -> float:
        """Predicted volatility scaled to an annualized percentage (industry-standard quote,
        comparable to e.g. the VIX regardless of this prediction's horizon)."""
        annualization_factor = math.sqrt(TRADING_DAYS_PER_YEAR / self.horizon_days)
        return self.predicted_volatility * annualization_factor * 100

    @property
    def expected_move_pct(self) -> float:
        """Expected +/- price move over the horizon, as a percentage of current price.

        Realized volatility over the horizon approximates the standard
        deviation of the cumulative log return over that same horizon, and
        for small values log-return percent change ~= simple percent change.
        """
        return self.predicted_volatility * 100

    @property
    def expected_move_dollars(self) -> float:
        """Expected +/- price move over the horizon, in dollars."""
        return self.current_price * self.predicted_volatility

    @property
    def expected_price_range(self) -> tuple[float, float]:
        """One-standard-deviation expected price range over the horizon: (low, high)."""
        move = self.expected_move_dollars
        return (self.current_price - move, self.current_price + move)


@dataclass(frozen=True, slots=True)
class ModelMetadata:
    """Metadata describing a trained model artifact — powers the model registry.

    `metrics` is the winning candidate's own cross-validated scores;
    `candidate_metrics` additionally keeps every candidate considered during
    model selection (keyed by algorithm name), so the "why this model won"
    comparison isn't discarded — it's what the model comparison page shows.
    """

    name: str
    version: str
    algorithm: str
    horizon_days: int
    trained_at: datetime
    feature_names: tuple[str, ...]
    metrics: dict[str, float]
    hyperparameters: dict[str, object]
    training_samples: int
    candidate_metrics: dict[str, dict[str, float]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.training_samples <= 0:
            raise DataValidationError("training_samples must be positive")
        if not self.feature_names:
            raise DataValidationError("feature_names cannot be empty")
        if self.horizon_days <= 0:
            raise DataValidationError("horizon_days must be positive")
