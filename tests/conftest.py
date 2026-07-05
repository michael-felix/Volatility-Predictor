"""Shared test fixtures/helpers for unit tests."""

import numpy as np
import pandas as pd


def synthetic_ohlcv(n_days: int = 80, seed: int = 42) -> pd.DataFrame:
    """Deterministic pseudo-random walk OHLCV frame, reused across feature/ML unit tests."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2026-01-01", periods=n_days, freq="B")
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n_days)))
    high = close * (1 + rng.uniform(0, 0.01, n_days))
    low = close * (1 - rng.uniform(0, 0.01, n_days))
    open_ = low + (high - low) * rng.uniform(0, 1, n_days)
    volume = rng.integers(1_000_000, 5_000_000, n_days)
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )
