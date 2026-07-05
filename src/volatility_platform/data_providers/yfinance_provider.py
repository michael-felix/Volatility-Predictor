"""yfinance-backed OHLCV data provider.

`yfinance` performs blocking HTTP calls under the hood, so every fetch
is offloaded to a worker thread via `asyncio.to_thread` — this provider
is used from async services/API code, and a blocking network call
directly on the event loop would stall every other concurrent request.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta

import pandas as pd
import yfinance as yf

from volatility_platform.domain.exceptions import DataProviderError, DataValidationError
from volatility_platform.domain.models import OHLCVBar, Ticker

logger = logging.getLogger(__name__)


class YFinanceProvider:
    """Fetches historical daily OHLCV bars from Yahoo Finance."""

    async def fetch_ohlcv(self, ticker: Ticker, start: date, end: date) -> list[OHLCVBar]:
        try:
            frame = await asyncio.to_thread(self._download, ticker, start, end)
        except Exception as exc:  # yfinance/requests can raise a variety of exception types
            raise DataProviderError(f"Failed to fetch data for {ticker}: {exc}") from exc

        if frame.empty:
            logger.warning("yfinance returned no data for %s between %s and %s", ticker, start, end)
            return []

        return self._to_bars(frame, ticker)

    @staticmethod
    def _download(ticker: Ticker, start: date, end: date) -> pd.DataFrame:
        # yfinance's `end` is exclusive; add a day so the requested end date is included.
        frame = yf.download(
            str(ticker),
            start=start.isoformat(),
            end=(end + timedelta(days=1)).isoformat(),
            interval="1d",
            progress=False,
            auto_adjust=True,
        )
        if isinstance(frame.columns, pd.MultiIndex):
            frame.columns = [str(c[0]).lower() for c in frame.columns]
        else:
            frame.columns = [str(c).lower() for c in frame.columns]
        return frame

    @staticmethod
    def _to_bars(frame: pd.DataFrame, ticker: Ticker) -> list[OHLCVBar]:
        bars: list[OHLCVBar] = []
        for index, row in frame.iterrows():
            trading_date = index.date() if isinstance(index, pd.Timestamp) else index
            try:
                bars.append(
                    OHLCVBar(
                        ticker=ticker,
                        trading_date=trading_date,
                        open=float(row["open"]),
                        high=float(row["high"]),
                        low=float(row["low"]),
                        close=float(row["close"]),
                        volume=int(row["volume"]),
                    )
                )
            except DataValidationError as exc:
                # yfinance occasionally returns a malformed row (e.g. around
                # corporate actions); skip just that row rather than failing
                # the whole ingestion run.
                logger.warning("Skipping invalid bar for %s on %s: %s", ticker, trading_date, exc)
        return bars
