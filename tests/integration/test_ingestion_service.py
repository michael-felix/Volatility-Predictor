"""Tests for IngestionService using a fake data provider and an in-memory
MongoDB mock (mongomock-motor) for the price repository."""

from datetime import date, timedelta

import pytest
from mongomock_motor import AsyncMongoMockClient

from volatility_platform.domain.exceptions import DataProviderError
from volatility_platform.domain.models import OHLCVBar, Ticker
from volatility_platform.repositories.price_repository import PriceRepository
from volatility_platform.services.ingestion_service import IngestionService


class FakeDataProvider:
    """Records every fetch call and returns one synthetic bar per day requested."""

    def __init__(self) -> None:
        self.calls: list[tuple[Ticker, date, date]] = []

    async def fetch_ohlcv(self, ticker: Ticker, start: date, end: date) -> list[OHLCVBar]:
        self.calls.append((ticker, start, end))
        bars = []
        current = start
        while current <= end:
            bars.append(OHLCVBar(ticker, current, 100.0, 101.0, 99.0, 100.5, 1_000_000))
            current += timedelta(days=1)
        return bars


class FlakyDataProvider(FakeDataProvider):
    """Raises for one specific ticker symbol, to test partial-failure handling."""

    async def fetch_ohlcv(self, ticker: Ticker, start: date, end: date) -> list[OHLCVBar]:
        if ticker.symbol == "BAD":
            raise DataProviderError("simulated provider outage")
        return await super().fetch_ohlcv(ticker, start, end)


@pytest.fixture
def price_repository() -> PriceRepository:
    return PriceRepository(AsyncMongoMockClient()["test_db"])


class TestIngestionService:
    async def test_first_ingest_uses_full_lookback_window(
        self, price_repository: PriceRepository
    ) -> None:
        provider = FakeDataProvider()
        service = IngestionService(provider, price_repository)
        ticker = Ticker("AAPL")

        written = await service.ingest_ticker(ticker, lookback_days=10)

        assert written == 11  # inclusive of both endpoints
        assert len(provider.calls) == 1
        _, start, end = provider.calls[0]
        assert (end - start).days == 10

    async def test_second_ingest_is_incremental(self, price_repository: PriceRepository) -> None:
        provider = FakeDataProvider()
        service = IngestionService(provider, price_repository)
        ticker = Ticker("AAPL")

        # Seed a bar dated several days ago directly, so "today" is guaranteed
        # to be later than the latest stored date regardless of when this test runs.
        stale_date = date.today() - timedelta(days=5)
        await price_repository.upsert_bars(
            [OHLCVBar(ticker, stale_date, 100.0, 101.0, 99.0, 100.5, 1_000_000)]
        )

        await service.ingest_ticker(ticker, lookback_days=10)

        assert len(provider.calls) == 1
        _, start, end = provider.calls[0]
        assert start == stale_date + timedelta(days=1)
        assert end == date.today()

    async def test_already_up_to_date_skips_fetch(self, price_repository: PriceRepository) -> None:
        provider = FakeDataProvider()
        service = IngestionService(provider, price_repository)
        ticker = Ticker("AAPL")

        first_written = await service.ingest_ticker(ticker, lookback_days=0)
        provider.calls.clear()
        second_written = await service.ingest_ticker(ticker, lookback_days=0)

        assert first_written == 1
        assert second_written == 0
        assert provider.calls == []

    async def test_ingest_tickers_continues_after_one_failure(
        self, price_repository: PriceRepository
    ) -> None:
        service = IngestionService(FlakyDataProvider(), price_repository)
        results = await service.ingest_tickers([Ticker("AAPL"), Ticker("BAD")], lookback_days=3)

        assert results["AAPL"] == 4
        assert results["BAD"] == 0
