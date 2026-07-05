"""Unit tests for the domain layer. Pure Python, no I/O, run in milliseconds."""

from datetime import UTC, date, datetime

import pytest

from volatility_platform.domain.exceptions import DataValidationError
from volatility_platform.domain.models import (
    ModelMetadata,
    OHLCVBar,
    Ticker,
    VolatilityPrediction,
)


class TestTicker:
    def test_normalizes_to_uppercase(self) -> None:
        assert Ticker("aapl").symbol == "AAPL"

    def test_strips_whitespace(self) -> None:
        assert Ticker("  msft  ").symbol == "MSFT"

    def test_accepts_dotted_symbol(self) -> None:
        assert Ticker("brk.b").symbol == "BRK.B"

    @pytest.mark.parametrize("bad_symbol", ["", "123", "TOOLONGTICKER", "AA PL"])
    def test_rejects_invalid_symbols(self, bad_symbol: str) -> None:
        with pytest.raises(DataValidationError):
            Ticker(bad_symbol)


class TestOHLCVBar:
    def _valid_kwargs(self) -> dict:
        return dict(
            ticker=Ticker("AAPL"),
            trading_date=date(2026, 1, 2),
            open=100.0,
            high=105.0,
            low=99.0,
            close=103.0,
            volume=1_000_000,
        )

    def test_valid_bar_constructs(self) -> None:
        bar = OHLCVBar(**self._valid_kwargs())
        assert bar.close == 103.0

    def test_rejects_high_below_low(self) -> None:
        kwargs = self._valid_kwargs()
        kwargs["high"] = 90.0
        with pytest.raises(DataValidationError):
            OHLCVBar(**kwargs)

    def test_rejects_negative_price(self) -> None:
        kwargs = self._valid_kwargs()
        kwargs["open"] = -1.0
        with pytest.raises(DataValidationError):
            OHLCVBar(**kwargs)

    def test_rejects_close_outside_range(self) -> None:
        kwargs = self._valid_kwargs()
        kwargs["close"] = 200.0
        with pytest.raises(DataValidationError):
            OHLCVBar(**kwargs)

    def test_rejects_negative_volume(self) -> None:
        kwargs = self._valid_kwargs()
        kwargs["volume"] = -5
        with pytest.raises(DataValidationError):
            OHLCVBar(**kwargs)


class TestVolatilityPrediction:
    def _valid_kwargs(self) -> dict:
        return dict(
            ticker=Ticker("AAPL"),
            horizon_days=5,
            predicted_volatility=0.023,
            current_price=200.0,
            model_name="rf_v1",
            model_version="2026.07.05",
            as_of_date=date(2026, 7, 5),
        )

    def test_valid_prediction_constructs(self) -> None:
        pred = VolatilityPrediction(**self._valid_kwargs())
        assert pred.predicted_volatility == 0.023
        assert pred.generated_at.tzinfo is not None

    def test_rejects_non_positive_horizon(self) -> None:
        kwargs = self._valid_kwargs()
        kwargs["horizon_days"] = 0
        with pytest.raises(DataValidationError):
            VolatilityPrediction(**kwargs)

    def test_rejects_negative_volatility(self) -> None:
        kwargs = self._valid_kwargs()
        kwargs["predicted_volatility"] = -0.01
        with pytest.raises(DataValidationError):
            VolatilityPrediction(**kwargs)

    def test_rejects_non_positive_current_price(self) -> None:
        kwargs = self._valid_kwargs()
        kwargs["current_price"] = 0.0
        with pytest.raises(DataValidationError):
            VolatilityPrediction(**kwargs)

    def test_annualized_volatility_pct(self) -> None:
        # rv over 5 days = 0.023 -> annualized = 0.023 * sqrt(252/5) * 100
        pred = VolatilityPrediction(**self._valid_kwargs())
        expected = 0.023 * (252 / 5) ** 0.5 * 100
        assert pred.annualized_volatility_pct == pytest.approx(expected)

    def test_expected_move_pct_and_dollars(self) -> None:
        pred = VolatilityPrediction(**self._valid_kwargs())
        assert pred.expected_move_pct == pytest.approx(2.3)
        assert pred.expected_move_dollars == pytest.approx(200.0 * 0.023)

    def test_expected_price_range_brackets_current_price(self) -> None:
        pred = VolatilityPrediction(**self._valid_kwargs())
        low, high = pred.expected_price_range
        move = pred.expected_move_dollars
        assert low == pytest.approx(200.0 - move)
        assert high == pytest.approx(200.0 + move)
        assert low < pred.current_price < high


class TestModelMetadata:
    def _valid_kwargs(self) -> dict:
        return dict(
            name="volatility_predictor",
            version="2026.07.05",
            algorithm="RandomForestRegressor",
            horizon_days=5,
            trained_at=datetime.now(UTC),
            feature_names=("log_return_1d", "realized_vol_5d"),
            metrics={"rmse": 0.012},
            hyperparameters={"n_estimators": 200},
            training_samples=500,
        )

    def test_valid_metadata_constructs(self) -> None:
        meta = ModelMetadata(**self._valid_kwargs())
        assert meta.training_samples == 500

    def test_rejects_zero_training_samples(self) -> None:
        kwargs = self._valid_kwargs()
        kwargs["training_samples"] = 0
        with pytest.raises(DataValidationError):
            ModelMetadata(**kwargs)

    def test_rejects_non_positive_horizon(self) -> None:
        kwargs = self._valid_kwargs()
        kwargs["horizon_days"] = 0
        with pytest.raises(DataValidationError):
            ModelMetadata(**kwargs)

    def test_rejects_empty_feature_names(self) -> None:
        kwargs = self._valid_kwargs()
        kwargs["feature_names"] = ()
        with pytest.raises(DataValidationError):
            ModelMetadata(**kwargs)
