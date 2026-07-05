"""Tests for TrainingService: pooling feature rows across tickers before training."""

import asyncio
from pathlib import Path

import pytest
from mongomock_motor import AsyncMongoMockClient

from volatility_platform.domain.exceptions import InsufficientDataError, TickerNotFoundError
from volatility_platform.domain.models import OHLCVBar, Ticker
from volatility_platform.ml.registry import FileSystemModelRegistry
from volatility_platform.repositories.price_repository import PriceRepository
from volatility_platform.services.training_service import TrainingService

from ..conftest import synthetic_ohlcv


async def _seed_ticker(repository: PriceRepository, symbol: str, n_days: int, seed: int) -> None:
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


@pytest.fixture
def price_repository() -> PriceRepository:
    return PriceRepository(AsyncMongoMockClient()["test_db"])


class TestTrainingService:
    async def test_pooling_two_tickers_yields_more_rows_than_one(
        self, price_repository: PriceRepository, tmp_path: Path
    ) -> None:
        await _seed_ticker(price_repository, "AAPL", n_days=150, seed=1)

        registry = FileSystemModelRegistry(store_path=str(tmp_path))
        service = TrainingService(price_repository, registry)

        single_metadata = await service.train_pooled_model(
            [Ticker("AAPL")], model_name="volatility_predictor", horizon_days=5
        )

        await _seed_ticker(price_repository, "MSFT", n_days=150, seed=2)
        pooled_metadata = await service.train_pooled_model(
            [Ticker("AAPL"), Ticker("MSFT")], model_name="volatility_predictor", horizon_days=5
        )

        assert pooled_metadata.training_samples > single_metadata.training_samples

    async def test_raises_when_ticker_has_no_stored_history(
        self, price_repository: PriceRepository, tmp_path: Path
    ) -> None:
        registry = FileSystemModelRegistry(store_path=str(tmp_path))
        service = TrainingService(price_repository, registry)

        with pytest.raises(TickerNotFoundError):
            await service.train_pooled_model(
                [Ticker("NVDA")], model_name="volatility_predictor", horizon_days=5
            )

    async def test_raises_when_no_ticker_has_enough_history(
        self, price_repository: PriceRepository, tmp_path: Path
    ) -> None:
        # 30 days is less than MIN_HISTORY_DAYS used inside build_feature_frame.
        await _seed_ticker(price_repository, "AAPL", n_days=30, seed=1)
        registry = FileSystemModelRegistry(store_path=str(tmp_path))
        service = TrainingService(price_repository, registry)

        with pytest.raises(InsufficientDataError):
            await service.train_pooled_model(
                [Ticker("AAPL")], model_name="volatility_predictor", horizon_days=5
            )

    async def test_trained_model_is_retrievable_from_registry(
        self, price_repository: PriceRepository, tmp_path: Path
    ) -> None:
        await _seed_ticker(price_repository, "AAPL", n_days=150, seed=1)
        registry = FileSystemModelRegistry(store_path=str(tmp_path))
        service = TrainingService(price_repository, registry)

        metadata = await service.train_pooled_model(
            [Ticker("AAPL")], model_name="volatility_predictor", horizon_days=5
        )

        _, loaded_metadata = await registry.load_model("volatility_predictor")
        assert loaded_metadata.version == metadata.version

    async def test_training_does_not_block_the_event_loop(
        self, price_repository: PriceRepository, tmp_path: Path
    ) -> None:
        """train_model cross-validates several CPU-bound models and must run
        off the event loop (see asyncio.to_thread in train_pooled_model) --
        otherwise it freezes the whole API for every concurrent request, not
        just the one that triggered training. A "heartbeat" coroutine ticking
        via asyncio.sleep can only make progress if the event loop is free;
        if training blocked it, the heartbeat count would stay near zero."""
        await _seed_ticker(price_repository, "AAPL", n_days=150, seed=1)
        registry = FileSystemModelRegistry(store_path=str(tmp_path))
        service = TrainingService(price_repository, registry)

        heartbeat_count = 0
        stop = False

        async def heartbeat() -> None:
            nonlocal heartbeat_count
            while not stop:
                heartbeat_count += 1
                await asyncio.sleep(0.01)

        heartbeat_task = asyncio.create_task(heartbeat())
        await service.train_pooled_model(
            [Ticker("AAPL")], model_name="volatility_predictor", horizon_days=5
        )
        stop = True
        await heartbeat_task

        assert heartbeat_count > 5
