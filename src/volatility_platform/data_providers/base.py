"""Abstract interface for OHLCV market data providers.

Adding a new source later (e.g. Alpha Vantage as a fallback) means
implementing this Protocol and constructing `services/` with a
different provider — no other code has to change.
"""

from datetime import date
from typing import Protocol

from volatility_platform.domain.models import OHLCVBar, Ticker


class DataProvider(Protocol):
    async def fetch_ohlcv(self, ticker: Ticker, start: date, end: date) -> list[OHLCVBar]: ...
