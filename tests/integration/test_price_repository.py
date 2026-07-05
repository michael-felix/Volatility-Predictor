"""Tests for PriceRepository against an in-memory MongoDB mock (mongomock-motor),
so these exercise real Mongo query/update semantics without a live database."""

from datetime import date

import pytest
from mongomock_motor import AsyncMongoMockClient

from volatility_platform.domain.models import OHLCVBar, Ticker
from volatility_platform.repositories.price_repository import PriceRepository


@pytest.fixture
def price_repository() -> PriceRepository:
    database = AsyncMongoMockClient()["test_db"]
    return PriceRepository(database)


def _bar(ticker: Ticker, day: date, close: float = 100.0) -> OHLCVBar:
    return OHLCVBar(ticker, day, close - 1, close + 1, close - 2, close, 1_000_000)


class TestPriceRepository:
    async def test_ensure_indexes_does_not_raise(self, price_repository: PriceRepository) -> None:
        await price_repository.ensure_indexes()

    async def test_upsert_and_get_bars(self, price_repository: PriceRepository) -> None:
        ticker = Ticker("AAPL")
        bars = [_bar(ticker, date(2026, 1, 2)), _bar(ticker, date(2026, 1, 5))]

        written = await price_repository.upsert_bars(bars)
        assert written == 2

        fetched = await price_repository.get_bars(ticker)
        assert [b.trading_date for b in fetched] == [date(2026, 1, 2), date(2026, 1, 5)]

    async def test_upsert_is_idempotent_and_overwrites(
        self, price_repository: PriceRepository
    ) -> None:
        ticker = Ticker("AAPL")
        await price_repository.upsert_bars([_bar(ticker, date(2026, 1, 2), close=100.0)])
        await price_repository.upsert_bars([_bar(ticker, date(2026, 1, 2), close=105.0)])

        fetched = await price_repository.get_bars(ticker)
        assert len(fetched) == 1
        assert fetched[0].close == 105.0

    async def test_get_bars_respects_date_range(self, price_repository: PriceRepository) -> None:
        ticker = Ticker("AAPL")
        bars = [_bar(ticker, date(2026, 1, d)) for d in range(1, 6)]
        await price_repository.upsert_bars(bars)

        fetched = await price_repository.get_bars(
            ticker, start=date(2026, 1, 2), end=date(2026, 1, 4)
        )
        assert [b.trading_date for b in fetched] == [
            date(2026, 1, 2),
            date(2026, 1, 3),
            date(2026, 1, 4),
        ]

    async def test_get_latest_date(self, price_repository: PriceRepository) -> None:
        ticker = Ticker("AAPL")
        await price_repository.upsert_bars(
            [_bar(ticker, date(2026, 1, 2)), _bar(ticker, date(2026, 1, 5))]
        )
        assert await price_repository.get_latest_date(ticker) == date(2026, 1, 5)

    async def test_get_latest_date_returns_none_when_no_data(
        self, price_repository: PriceRepository
    ) -> None:
        assert await price_repository.get_latest_date(Ticker("MSFT")) is None

    async def test_upsert_empty_list_is_a_noop(self, price_repository: PriceRepository) -> None:
        assert await price_repository.upsert_bars([]) == 0

    async def test_tickers_are_isolated_from_each_other(
        self, price_repository: PriceRepository
    ) -> None:
        aapl, msft = Ticker("AAPL"), Ticker("MSFT")
        await price_repository.upsert_bars([_bar(aapl, date(2026, 1, 2))])
        await price_repository.upsert_bars([_bar(msft, date(2026, 1, 2))])

        assert len(await price_repository.get_bars(aapl)) == 1
        assert len(await price_repository.get_bars(msft)) == 1
