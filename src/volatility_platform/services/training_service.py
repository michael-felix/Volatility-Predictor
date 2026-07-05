"""Training orchestration: build a pooled feature dataset across multiple
tickers, select/train the best model, and persist it through the active
model registry.

Pooling feature rows from multiple tickers (rather than training a
separate model per ticker) directly addresses the small-sample problem
observed with a single ticker's ~2 years of daily history — features are
already scale-invariant (log returns, SMA ratios), so rows from
different tickers combine validly into one training set, and the
resulting model can score any ticker with enough stored history, not
just ones it happened to be trained on.
"""

from __future__ import annotations

import logging

import pandas as pd

from volatility_platform.domain.exceptions import InsufficientDataError, TickerNotFoundError
from volatility_platform.domain.models import ModelMetadata, Ticker
from volatility_platform.features.pipeline import bars_to_dataframe, build_feature_frame
from volatility_platform.ml.registry import ModelRegistryProtocol
from volatility_platform.ml.train import train_model
from volatility_platform.repositories.price_repository import PriceRepository

logger = logging.getLogger(__name__)


class TrainingService:
    """Orchestrates: fetch stored price history -> pooled features -> train -> persist."""

    def __init__(
        self, price_repository: PriceRepository, model_registry: ModelRegistryProtocol
    ) -> None:
        self._price_repository = price_repository
        self._model_registry = model_registry

    async def train_pooled_model(
        self, tickers: list[Ticker], model_name: str, horizon_days: int
    ) -> ModelMetadata:
        """Train one model on feature rows pooled across all `tickers`.

        Tickers with too little stored history to build features are
        skipped (logged, not fatal) rather than failing the whole run —
        useful right after a new ticker has just started being ingested.
        """
        per_ticker_frames: list[pd.DataFrame] = []
        for ticker in tickers:
            bars = await self._price_repository.get_bars(ticker)
            if not bars:
                raise TickerNotFoundError(f"No stored price history for {ticker}")

            ohlcv = bars_to_dataframe(bars)
            try:
                frame = build_feature_frame(ohlcv, horizon=horizon_days, include_target=True)
            except InsufficientDataError:
                logger.warning("Skipping %s: not enough history to build features yet", ticker)
                continue
            per_ticker_frames.append(frame)

        if not per_ticker_frames:
            raise InsufficientDataError(
                "None of the requested tickers have enough history to build features"
            )

        pooled_frame = pd.concat(per_ticker_frames).sort_index()

        model, metadata = train_model(
            pooled_frame, model_name=model_name, horizon_days=horizon_days
        )
        await self._model_registry.save_model(model, metadata)
        return metadata
