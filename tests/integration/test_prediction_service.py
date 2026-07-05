"""Tests for PredictionService: stored history -> features -> model -> persisted prediction."""

from pathlib import Path

import pytest
from mongomock_motor import AsyncMongoMockClient

from volatility_platform.domain.exceptions import TickerNotFoundError
from volatility_platform.domain.models import OHLCVBar, Ticker
from volatility_platform.ml.registry import FileSystemModelRegistry
from volatility_platform.repositories.prediction_repository import PredictionRepository
from volatility_platform.repositories.price_repository import PriceRepository
from volatility_platform.services.prediction_service import PredictionService
from volatility_platform.services.training_service import TrainingService

from ..conftest import synthetic_ohlcv


async def _seed_ticker(repository: PriceRepository, symbol: str, n_days: int, seed: int) -> Ticker:
    ticker = Ticker(symbol)
    ohlcv = synthetic_ohlcv(n_days=n_days, seed=seed)
    bars = [
        OHLCVBar(
            ticker,
            idx.date(),
            row["open"],
            row["high"],
            row["low"],
            row["close"],
            int(row["volume"]),
        )
        for idx, row in ohlcv.iterrows()
    ]
    await repository.upsert_bars(bars)
    return ticker


@pytest.fixture
def price_repository() -> PriceRepository:
    return PriceRepository(AsyncMongoMockClient()["test_db"])


@pytest.fixture
def prediction_repository() -> PredictionRepository:
    return PredictionRepository(AsyncMongoMockClient()["test_db"])


class TestPredictionService:
    async def test_predict_returns_and_persists_prediction(
        self,
        price_repository: PriceRepository,
        prediction_repository: PredictionRepository,
        tmp_path: Path,
    ) -> None:
        ticker = await _seed_ticker(price_repository, "AAPL", n_days=150, seed=1)
        registry = FileSystemModelRegistry(store_path=str(tmp_path))

        await TrainingService(price_repository, registry).train_pooled_model(
            [ticker], model_name="volatility_predictor", horizon_days=5
        )

        service = PredictionService(price_repository, prediction_repository, registry)
        prediction = await service.predict(ticker, model_name="volatility_predictor")

        assert prediction.ticker == ticker
        assert prediction.predicted_volatility >= 0.0
        assert prediction.current_price > 0

        history = await service.get_prediction_history(ticker)
        assert len(history) == 1
        assert history[0].model_version == prediction.model_version

    async def test_predict_raises_for_ticker_with_no_history(
        self,
        price_repository: PriceRepository,
        prediction_repository: PredictionRepository,
        tmp_path: Path,
    ) -> None:
        registry = FileSystemModelRegistry(store_path=str(tmp_path))
        service = PredictionService(price_repository, prediction_repository, registry)

        with pytest.raises(TickerNotFoundError):
            await service.predict(Ticker("NVDA"), model_name="volatility_predictor")

    async def test_prediction_history_accumulates_across_calls(
        self,
        price_repository: PriceRepository,
        prediction_repository: PredictionRepository,
        tmp_path: Path,
    ) -> None:
        ticker = await _seed_ticker(price_repository, "AAPL", n_days=150, seed=1)
        registry = FileSystemModelRegistry(store_path=str(tmp_path))
        await TrainingService(price_repository, registry).train_pooled_model(
            [ticker], model_name="volatility_predictor", horizon_days=5
        )

        service = PredictionService(price_repository, prediction_repository, registry)
        await service.predict(ticker, model_name="volatility_predictor")
        await service.predict(ticker, model_name="volatility_predictor")

        history = await service.get_prediction_history(ticker)
        assert len(history) == 2
