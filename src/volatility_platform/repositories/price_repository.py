"""MongoDB-backed repository for historical OHLCV price bars.

One document per (ticker, trading_date). Dates are stored as ISO
strings rather than BSON dates so `trading_date` (a `datetime.date`
domain value, no time-of-day) round-trips exactly rather than picking
up a spurious midnight/UTC time component.
"""

from __future__ import annotations

import asyncio
from datetime import date
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, IndexModel

from volatility_platform.domain.models import OHLCVBar, Ticker

COLLECTION_NAME = "historical_prices"


class PriceRepository:
    """Stores and retrieves OHLCV bars for tickers."""

    def __init__(self, database: AsyncIOMotorDatabase[dict[str, Any]]) -> None:
        self._collection = database[COLLECTION_NAME]

    async def ensure_indexes(self) -> None:
        await self._collection.create_indexes(
            [IndexModel([("ticker", ASCENDING), ("trading_date", ASCENDING)], unique=True)]
        )

    async def upsert_bars(self, bars: list[OHLCVBar]) -> int:
        """Upsert bars keyed on (ticker, trading_date). Re-ingesting the same day is
        idempotent — it overwrites rather than duplicates. Returns the number of
        bars written.

        Runs upserts concurrently via `asyncio.gather` rather than a single
        `bulk_write` — at this project's data volumes (hundreds of rows per
        ticker) the performance difference is negligible, and it avoids a
        `pymongo`/`mongomock` bulk-write incompatibility in the test suite.
        """
        if not bars:
            return 0

        async def _upsert_one(bar: OHLCVBar) -> None:
            await self._collection.update_one(
                {"ticker": bar.ticker.symbol, "trading_date": bar.trading_date.isoformat()},
                {"$set": self._to_document(bar)},
                upsert=True,
            )

        await asyncio.gather(*(_upsert_one(bar) for bar in bars))
        return len(bars)

    async def get_bars(
        self, ticker: Ticker, start: date | None = None, end: date | None = None
    ) -> list[OHLCVBar]:
        """Fetch bars for a ticker, optionally bounded by [start, end], sorted ascending."""
        query: dict[str, Any] = {"ticker": ticker.symbol}
        date_filter: dict[str, Any] = {}
        if start is not None:
            date_filter["$gte"] = start.isoformat()
        if end is not None:
            date_filter["$lte"] = end.isoformat()
        if date_filter:
            query["trading_date"] = date_filter

        cursor = self._collection.find(query).sort("trading_date", ASCENDING)
        documents = await cursor.to_list(length=None)
        return [self._to_domain(doc, ticker) for doc in documents]

    async def get_latest_date(self, ticker: Ticker) -> date | None:
        """Most recent trading date stored for `ticker`, or None if there's no data yet.

        Used by the ingestion pipeline to decide how far back an
        incremental update needs to fetch.
        """
        doc = await self._collection.find_one(
            {"ticker": ticker.symbol}, sort=[("trading_date", -1)]
        )
        return date.fromisoformat(doc["trading_date"]) if doc else None

    async def count_bars(self, ticker: Ticker) -> int:
        """Number of stored bars for `ticker`, without loading them (used by GET /tickers)."""
        return await self._collection.count_documents({"ticker": ticker.symbol})

    @staticmethod
    def _to_document(bar: OHLCVBar) -> dict[str, Any]:
        return {
            "ticker": bar.ticker.symbol,
            "trading_date": bar.trading_date.isoformat(),
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume,
        }

    @staticmethod
    def _to_domain(doc: dict[str, Any], ticker: Ticker) -> OHLCVBar:
        return OHLCVBar(
            ticker=ticker,
            trading_date=date.fromisoformat(doc["trading_date"]),
            open=doc["open"],
            high=doc["high"],
            low=doc["low"],
            close=doc["close"],
            volume=doc["volume"],
        )
