"""Ingestion orchestration: fetch OHLCV history from a data provider and
persist it via the price repository.

Kept separate from `prediction_service`/`training_service` because
ingestion runs on its own schedule (a cron-style pipeline script, not a
request-driven API call) and has different failure semantics: a failed
fetch for one ticker today can simply retry tomorrow, and one ticker
failing shouldn't abort ingestion for the rest.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

from volatility_platform.data_providers.base import DataProvider
from volatility_platform.domain.exceptions import DataProviderError
from volatility_platform.domain.models import Ticker
from volatility_platform.repositories.price_repository import PriceRepository

logger = logging.getLogger(__name__)


class IngestionService:
    """Orchestrates: fetch from provider -> validate (via OHLCVBar) -> upsert."""

    def __init__(self, data_provider: DataProvider, price_repository: PriceRepository) -> None:
        self._data_provider = data_provider
        self._price_repository = price_repository

    async def ingest_ticker(self, ticker: Ticker, lookback_days: int) -> int:
        """Fetch and store OHLCV history for a single ticker.

        Incremental by default: if data already exists for this ticker,
        only fetches from the day after the latest stored date through
        today, rather than re-downloading the full history every run.
        """
        latest_date = await self._price_repository.get_latest_date(ticker)
        end = date.today()
        start = (
            latest_date + timedelta(days=1)
            if latest_date is not None
            else end - timedelta(days=lookback_days)
        )
        if start > end:
            return 0  # already up to date

        bars = await self._data_provider.fetch_ohlcv(ticker, start, end)
        return await self._price_repository.upsert_bars(bars)

    async def ingest_tickers(self, tickers: list[Ticker], lookback_days: int) -> dict[str, int]:
        """Ingest multiple tickers; one ticker's provider failure is logged and
        skipped rather than aborting ingestion for the rest."""
        results: dict[str, int] = {}
        for ticker in tickers:
            try:
                results[ticker.symbol] = await self.ingest_ticker(ticker, lookback_days)
            except DataProviderError:
                logger.exception(
                    "Ingestion failed for %s; continuing with remaining tickers", ticker
                )
                results[ticker.symbol] = 0
        return results
