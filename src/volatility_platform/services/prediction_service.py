"""Prediction orchestration: fetch stored price history, build features
via the exact same pipeline used at training time, run inference through
the active model registry's model, and persist the result for the
prediction-history endpoint.
"""

from __future__ import annotations

from volatility_platform.domain.exceptions import TickerNotFoundError
from volatility_platform.domain.models import Ticker, VolatilityPrediction
from volatility_platform.features.pipeline import bars_to_dataframe, build_feature_frame
from volatility_platform.ml.predict import predict_volatility
from volatility_platform.ml.registry import ModelRegistryProtocol
from volatility_platform.repositories.prediction_repository import PredictionRepository
from volatility_platform.repositories.price_repository import PriceRepository


class PredictionService:
    """Orchestrates: stored history -> features -> model inference -> persisted prediction."""

    def __init__(
        self,
        price_repository: PriceRepository,
        prediction_repository: PredictionRepository,
        model_registry: ModelRegistryProtocol,
    ) -> None:
        self._price_repository = price_repository
        self._prediction_repository = prediction_repository
        self._model_registry = model_registry

    async def predict(self, ticker: Ticker, model_name: str) -> VolatilityPrediction:
        bars = await self._price_repository.get_bars(ticker)
        if not bars:
            raise TickerNotFoundError(f"No stored price history for {ticker}")

        ohlcv = bars_to_dataframe(bars)
        feature_frame = build_feature_frame(ohlcv, include_target=False)
        current_price = float(ohlcv["close"].iloc[-1])

        model, metadata = await self._model_registry.load_model(model_name)
        prediction = predict_volatility(model, metadata, feature_frame, ticker, current_price)

        await self._prediction_repository.save_prediction(prediction)
        return prediction

    async def get_prediction_history(
        self, ticker: Ticker, limit: int = 50
    ) -> list[VolatilityPrediction]:
        return await self._prediction_repository.get_predictions(ticker, limit=limit)
