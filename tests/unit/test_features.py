"""Unit tests for the feature engineering pipeline.

Uses synthetic price series with hand-computable expected values where
possible, so failures point at exactly which calculation broke.
"""

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from volatility_platform.domain.exceptions import InsufficientDataError
from volatility_platform.domain.models import OHLCVBar, Ticker
from volatility_platform.features.pipeline import (
    MIN_HISTORY_DAYS,
    bars_to_dataframe,
    build_feature_frame,
    compute_target,
)
from volatility_platform.features.returns import log_returns, simple_returns
from volatility_platform.features.volatility import har_features, realized_volatility

from ..conftest import synthetic_ohlcv as _synthetic_ohlcv


class TestReturns:
    def test_simple_returns_known_values(self) -> None:
        close = pd.Series([100.0, 110.0, 99.0])
        result = simple_returns(close)
        assert result.iloc[1] == pytest.approx(0.10)
        assert result.iloc[2] == pytest.approx(-0.10)
        assert pd.isna(result.iloc[0])

    def test_log_returns_known_values(self) -> None:
        close = pd.Series([100.0, 110.0])
        result = log_returns(close)
        assert result.iloc[1] == pytest.approx(np.log(1.10))


class TestVolatility:
    def test_realized_volatility_matches_manual_calc(self) -> None:
        rets = pd.Series([0.01, -0.02, 0.03])
        rv = realized_volatility(rets, window=3)
        expected = (0.01**2 + 0.02**2 + 0.03**2) ** 0.5
        assert rv.iloc[-1] == pytest.approx(expected)

    def test_har_features_has_expected_columns(self) -> None:
        rets = pd.Series(np.random.default_rng(0).normal(0, 0.01, 30))
        result = har_features(rets)
        assert set(result.columns) == {"rv_daily", "rv_weekly", "rv_monthly"}


class TestComputeTarget:
    def test_target_matches_manual_forward_sum(self) -> None:
        rets = pd.Series([0.01, 0.02, -0.01, 0.03, -0.02, 0.01])
        horizon = 2
        target = compute_target(rets, horizon)
        # At row 1 (index label 1), forward window is rows 2 and 3: (-0.01, 0.03)
        expected = ((-0.01) ** 2 + 0.03**2) ** 0.5
        assert target.iloc[1] == pytest.approx(expected)

    def test_target_is_nan_near_series_end(self) -> None:
        rets = pd.Series([0.01, 0.02, -0.01, 0.03])
        target = compute_target(rets, horizon=2)
        # Last two rows have no full forward window available.
        assert pd.isna(target.iloc[-1])
        assert pd.isna(target.iloc[-2])


class TestBarsToDataFrame:
    def test_converts_and_sorts_bars(self) -> None:
        today = date(2026, 1, 5)
        bars = [
            OHLCVBar(Ticker("AAPL"), today, 100, 101, 99, 100.5, 1000),
            OHLCVBar(Ticker("AAPL"), today - timedelta(days=1), 98, 100, 97, 99.5, 900),
        ]
        frame = bars_to_dataframe(bars)
        assert list(frame.index) == sorted(frame.index)
        assert list(frame.columns) == ["open", "high", "low", "close", "volume"]

    def test_empty_bar_list_raises(self) -> None:
        with pytest.raises(InsufficientDataError):
            bars_to_dataframe([])


class TestBuildFeatureFrame:
    def test_raises_when_not_enough_history(self) -> None:
        short_ohlcv = _synthetic_ohlcv(n_days=MIN_HISTORY_DAYS - 1)
        with pytest.raises(InsufficientDataError):
            build_feature_frame(short_ohlcv)

    def test_produces_no_nans_and_expected_columns(self) -> None:
        ohlcv = _synthetic_ohlcv(n_days=80)
        result = build_feature_frame(ohlcv, horizon=5)

        assert not result.isna().any().any()
        assert "target" in result.columns
        assert "rv_daily" in result.columns
        assert "sma_5_ratio" in result.columns
        assert "log_return_lag_1" in result.columns
        assert "day_of_week" in result.columns

    def test_excludes_target_when_requested(self) -> None:
        ohlcv = _synthetic_ohlcv(n_days=80)
        result = build_feature_frame(ohlcv, include_target=False)
        assert "target" not in result.columns

    def test_inference_and_training_frames_share_feature_values(self) -> None:
        """Guards against train/serve skew: feature columns must be identical
        whether or not the target is requested, since inference always
        calls with include_target=False."""
        ohlcv = _synthetic_ohlcv(n_days=80)
        train_frame = build_feature_frame(ohlcv, horizon=5, include_target=True)
        infer_frame = build_feature_frame(ohlcv, horizon=5, include_target=False)

        shared_index = train_frame.index.intersection(infer_frame.index)
        feature_cols = [c for c in train_frame.columns if c != "target"]
        pd.testing.assert_frame_equal(
            train_frame.loc[shared_index, feature_cols],
            infer_frame.loc[shared_index, feature_cols],
        )
