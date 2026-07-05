"""Tests for PredictionRepository against an in-memory MongoDB mock (mongomock-motor)."""

from datetime import date

import pytest
from mongomock_motor import AsyncMongoMockClient

from volatility_platform.domain.models import Ticker, VolatilityPrediction
from volatility_platform.repositories.prediction_repository import PredictionRepository


@pytest.fixture
def prediction_repository() -> PredictionRepository:
    database = AsyncMongoMockClient()["test_db"]
    return PredictionRepository(database)


def _prediction(ticker: Ticker, as_of: date, volatility: float = 0.02) -> VolatilityPrediction:
    return VolatilityPrediction(
        ticker=ticker,
        horizon_days=5,
        predicted_volatility=volatility,
        current_price=200.0,
        model_name="volatility_predictor",
        model_version="20260705_000000",
        as_of_date=as_of,
    )


class TestPredictionRepository:
    async def test_ensure_indexes_does_not_raise(
        self, prediction_repository: PredictionRepository
    ) -> None:
        await prediction_repository.ensure_indexes()

    async def test_save_and_retrieve_prediction(
        self, prediction_repository: PredictionRepository
    ) -> None:
        ticker = Ticker("AAPL")
        prediction = _prediction(ticker, date(2026, 7, 5))

        await prediction_repository.save_prediction(prediction)
        results = await prediction_repository.get_predictions(ticker)

        assert len(results) == 1
        assert results[0].predicted_volatility == pytest.approx(0.02)
        assert results[0].as_of_date == date(2026, 7, 5)

    async def test_get_predictions_returns_newest_first(
        self, prediction_repository: PredictionRepository
    ) -> None:
        ticker = Ticker("AAPL")
        await prediction_repository.save_prediction(_prediction(ticker, date(2026, 7, 1), 0.01))
        await prediction_repository.save_prediction(_prediction(ticker, date(2026, 7, 5), 0.02))

        results = await prediction_repository.get_predictions(ticker)
        assert [r.as_of_date for r in results] == [date(2026, 7, 5), date(2026, 7, 1)]

    async def test_get_predictions_respects_limit(
        self, prediction_repository: PredictionRepository
    ) -> None:
        ticker = Ticker("AAPL")
        for day in range(1, 6):
            await prediction_repository.save_prediction(_prediction(ticker, date(2026, 7, day)))

        results = await prediction_repository.get_predictions(ticker, limit=2)
        assert len(results) == 2

    async def test_predictions_are_isolated_per_ticker(
        self, prediction_repository: PredictionRepository
    ) -> None:
        await prediction_repository.save_prediction(_prediction(Ticker("AAPL"), date(2026, 7, 5)))
        await prediction_repository.save_prediction(_prediction(Ticker("MSFT"), date(2026, 7, 5)))

        assert len(await prediction_repository.get_predictions(Ticker("AAPL"))) == 1
        assert len(await prediction_repository.get_predictions(Ticker("MSFT"))) == 1
