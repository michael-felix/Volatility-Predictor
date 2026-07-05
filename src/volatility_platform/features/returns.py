"""Return calculations from a series of closing prices.

All functions take/return `pandas.Series` indexed by trading date and
contain a leading NaN (there is no return on the first observed day).
Callers are expected to handle NaNs via `dropna()` at the end of the
pipeline, not inside each individual feature function — keeping NaN
handling in one place makes it easy to reason about how many rows of
history are consumed before the feature set becomes valid.
"""

import numpy as np
import pandas as pd


def simple_returns(close: pd.Series) -> pd.Series:
    """Day-over-day percentage return: (P_t / P_{t-1}) - 1."""
    return close.pct_change()


def log_returns(close: pd.Series) -> pd.Series:
    """Day-over-day log return: ln(P_t / P_{t-1}).

    Preferred over simple returns for volatility modeling because log
    returns are additive across time (useful for multi-day realized
    volatility sums) and better approximate a normal distribution.
    """
    return np.log(close / close.shift(1))
