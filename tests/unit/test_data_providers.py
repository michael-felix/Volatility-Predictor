"""Unit tests for YFinanceProvider. `yf.download` is monkeypatched so these
run without any real network access."""

from datetime import date

import pandas as pd
import pytest

from volatility_platform.data_providers.yfinance_provider import YFinanceProvider
from volatility_platform.domain.exceptions import DataProviderError
from volatility_platform.domain.models import Ticker


def _fake_yf_frame(bad_row: bool = False) -> pd.DataFrame:
    dates = pd.date_range("2026-01-02", periods=3, freq="D")
    close = [100.5, 101.5, 102.5]
    high = [101.0, 102.0, 103.0]
    if bad_row:
        close[1] = 500.0  # close far outside [low, high] -> fails OHLCVBar validation
    return pd.DataFrame(
        {
            "Open": [100.0, 101.0, 102.0],
            "High": high,
            "Low": [99.0, 100.0, 101.0],
            "Close": close,
            "Volume": [1_000_000, 1_100_000, 1_200_000],
        },
        index=dates,
    )


class TestYFinanceProvider:
    async def test_fetch_ohlcv_converts_to_domain_bars(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "volatility_platform.data_providers.yfinance_provider.yf.download",
            lambda *args, **kwargs: _fake_yf_frame(),
        )
        provider = YFinanceProvider()
        bars = await provider.fetch_ohlcv(Ticker("AAPL"), date(2026, 1, 2), date(2026, 1, 4))

        assert len(bars) == 3
        assert bars[0].close == 100.5
        assert bars[0].ticker.symbol == "AAPL"
        assert bars[0].trading_date == date(2026, 1, 2)

    async def test_empty_frame_returns_empty_list(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "volatility_platform.data_providers.yfinance_provider.yf.download",
            lambda *args, **kwargs: pd.DataFrame(),
        )
        provider = YFinanceProvider()
        bars = await provider.fetch_ohlcv(Ticker("ZZZZ"), date(2026, 1, 2), date(2026, 1, 4))
        assert bars == []

    async def test_download_failure_raises_data_provider_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _raise(*args: object, **kwargs: object) -> pd.DataFrame:
            raise RuntimeError("network error")

        monkeypatch.setattr(
            "volatility_platform.data_providers.yfinance_provider.yf.download", _raise
        )
        provider = YFinanceProvider()
        with pytest.raises(DataProviderError):
            await provider.fetch_ohlcv(Ticker("AAPL"), date(2026, 1, 2), date(2026, 1, 4))

    async def test_skips_invalid_row_but_keeps_valid_ones(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "volatility_platform.data_providers.yfinance_provider.yf.download",
            lambda *args, **kwargs: _fake_yf_frame(bad_row=True),
        )
        provider = YFinanceProvider()
        bars = await provider.fetch_ohlcv(Ticker("AAPL"), date(2026, 1, 2), date(2026, 1, 4))

        assert len(bars) == 2
        assert all(b.trading_date != date(2026, 1, 3) for b in bars)
