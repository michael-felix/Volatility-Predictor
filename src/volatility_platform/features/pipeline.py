"""Single composed feature-engineering pipeline.

`build_feature_frame` is the ONE function both training (`ml/train.py`)
and inference (the `/predict` route, via `ml/predict.py`) call to turn
raw OHLCV history into a model-ready feature frame. Never duplicate this
logic elsewhere — that duplication is exactly how train/serve skew
happens.
"""

from __future__ import annotations

import pandas as pd

from volatility_platform.domain.exceptions import InsufficientDataError
from volatility_platform.domain.models import OHLCVBar
from volatility_platform.features.returns import log_returns
from volatility_platform.features.volatility import har_features, rolling_std, rolling_variance

# Longest lookback window used by any feature (HAR monthly component).
# Any row without this many prior observations can't have valid features.
MIN_HISTORY_DAYS = 22

LAG_PERIODS = (1, 2, 3, 5)
MA_WINDOWS = (5, 10, 20)
STD_WINDOWS = (5, 10, 20)


def bars_to_dataframe(bars: list[OHLCVBar]) -> pd.DataFrame:
    """Convert domain `OHLCVBar` objects (single ticker) into a sorted, indexed DataFrame."""
    if not bars:
        raise InsufficientDataError("Cannot build a DataFrame from an empty bar list")
    frame = pd.DataFrame(
        {
            # pd.to_datetime ensures the index below is a real DatetimeIndex
            # (not a plain object Index of `datetime.date`), which
            # `_time_features` relies on for `.dayofweek`/`.month`.
            "trading_date": pd.to_datetime([b.trading_date for b in bars]),
            "open": [b.open for b in bars],
            "high": [b.high for b in bars],
            "low": [b.low for b in bars],
            "close": [b.close for b in bars],
            "volume": [b.volume for b in bars],
        }
    )
    frame = frame.sort_values("trading_date").set_index("trading_date")
    return frame


def _moving_averages(close: pd.Series) -> pd.DataFrame:
    """Simple moving averages of close price, expressed as a ratio to current close.

    Expressing as `sma / close` rather than the raw SMA level keeps the
    feature scale comparable across tickers with very different share
    prices (e.g. a $15 stock vs. a $3,000 stock).
    """
    return pd.DataFrame(
        {f"sma_{w}_ratio": close.rolling(window=w).mean() / close for w in MA_WINDOWS}
    )


def _lag_features(log_rets: pd.Series) -> pd.DataFrame:
    """Lagged log returns — gives the model direct access to recent return history."""
    return pd.DataFrame({f"log_return_lag_{lag}": log_rets.shift(lag) for lag in LAG_PERIODS})


def _rolling_dispersion(log_rets: pd.Series) -> pd.DataFrame:
    """Rolling standard deviation and variance of returns at multiple windows."""
    cols: dict[str, pd.Series] = {}
    for w in STD_WINDOWS:
        cols[f"rolling_std_{w}"] = rolling_std(log_rets, w)
        cols[f"rolling_var_{w}"] = rolling_variance(log_rets, w)
    return pd.DataFrame(cols)


def _time_features(index: pd.DatetimeIndex) -> pd.DataFrame:
    """Calendar features: day-of-week and month can capture mild seasonal effects
    (e.g. elevated volatility around monthly options expiry)."""
    return pd.DataFrame(
        {
            "day_of_week": index.dayofweek,
            "month": index.month,
        },
        index=index,
    )


def compute_target(log_rets: pd.Series, horizon: int) -> pd.Series:
    """Forward realized volatility over the next `horizon` trading days.

    This is the ONLY deliberately forward-looking calculation in the
    pipeline — it is the label, not a feature, and must never be joined
    into the feature matrix used at inference time.

    Implementation note: `s.rolling(horizon).sum()` at row `t + horizon`
    equals `sum(s[t+1 : t+horizon+1])`. Shifting the result back by
    `horizon` therefore aligns "sum of the next `horizon` days" onto row
    `t`, without an explicit reversal of the series.
    """
    squared = log_rets.pow(2)
    forward_sum = squared.rolling(window=horizon).sum().shift(-horizon)
    return forward_sum.pow(0.5)


def build_feature_frame(
    ohlcv: pd.DataFrame, horizon: int = 5, include_target: bool = True
) -> pd.DataFrame:
    """Build the full model-ready feature frame from raw OHLCV data.

    Args:
        ohlcv: DataFrame for a SINGLE ticker, indexed by trading date,
            with columns open/high/low/close/volume, sorted ascending.
        horizon: number of forward trading days the target represents.
            Ignored if `include_target` is False.
        include_target: whether to compute and attach the `target`
            column. False for inference (there is no future to label);
            True for training.

    Returns:
        A DataFrame with one row per valid trading date, feature
        columns, and (if requested) a `target` column. Rows that don't
        have enough history/future data for every column are dropped.
    """
    if len(ohlcv) < MIN_HISTORY_DAYS:
        raise InsufficientDataError(
            f"Need at least {MIN_HISTORY_DAYS} rows of history, got {len(ohlcv)}"
        )

    close = ohlcv["close"]
    log_rets = log_returns(close)

    feature_blocks = [
        pd.DataFrame({"log_return": log_rets}),
        har_features(log_rets),
        _rolling_dispersion(log_rets),
        _moving_averages(close),
        _lag_features(log_rets),
        _time_features(ohlcv.index),
    ]
    features = pd.concat(feature_blocks, axis=1)

    if include_target:
        features["target"] = compute_target(log_rets, horizon)

    return features.dropna()
