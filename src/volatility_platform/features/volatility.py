"""Volatility feature calculations built on top of log returns.

Convention used throughout this module: a value at row `t` is computed
using only log returns up to and including day `t` — i.e. it represents
information an observer would actually have at the close of trading on
day `t`. This is what makes these safe to use as model *features* (as
opposed to the *target*, which is deliberately forward-looking and lives
in `pipeline.py::compute_target`).
"""

import numpy as np
import pandas as pd

from volatility_platform.domain.models import TRADING_DAYS_PER_YEAR


def realized_volatility(log_rets: pd.Series, window: int, annualize: bool = False) -> pd.Series:
    """Realized volatility: sqrt of the sum of squared log returns over `window` days.

    This is the standard realized-volatility estimator (root sum of
    squares, not root *mean* of squares) used in the HAR-RV literature.
    """
    rv = log_rets.pow(2).rolling(window=window).sum().pow(0.5)
    if annualize:
        rv = rv * np.sqrt(TRADING_DAYS_PER_YEAR / window)
    return rv


def rolling_std(log_rets: pd.Series, window: int) -> pd.Series:
    """Rolling standard deviation of log returns over `window` days."""
    return log_rets.rolling(window=window).std()


def rolling_variance(log_rets: pd.Series, window: int) -> pd.Series:
    """Rolling variance of log returns over `window` days."""
    return log_rets.rolling(window=window).var()


def har_features(log_rets: pd.Series) -> pd.DataFrame:
    """HAR-RV components: daily, weekly-average, monthly-average realized volatility.

    Based on Corsi's Heterogeneous Autoregressive model of Realized
    Volatility (HAR-RV), which approximates long-memory volatility
    clustering using just three horizons instead of many AR lags:

    - rv_daily: realized volatility using only the prior day's return
    - rv_weekly: realized volatility over the trailing 5 trading days
    - rv_monthly: realized volatility over the trailing 22 trading days
    """
    return pd.DataFrame(
        {
            "rv_daily": realized_volatility(log_rets, window=1),
            "rv_weekly": realized_volatility(log_rets, window=5),
            "rv_monthly": realized_volatility(log_rets, window=22),
        }
    )
