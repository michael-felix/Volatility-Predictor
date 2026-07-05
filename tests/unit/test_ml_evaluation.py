import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LinearRegression

from volatility_platform.domain.exceptions import InsufficientDataError
from volatility_platform.ml.evaluation import qlike_loss, regression_metrics, time_series_cv_scores


class TestRegressionMetrics:
    def test_perfect_predictions_give_zero_error_and_r2_one(self) -> None:
        y_true = pd.Series([1.0, 2.0, 3.0, 4.0])
        metrics = regression_metrics(y_true, y_true.to_numpy())
        assert metrics["rmse"] == pytest.approx(0.0)
        assert metrics["mae"] == pytest.approx(0.0)
        assert metrics["r2"] == pytest.approx(1.0)
        assert metrics["qlike"] == pytest.approx(0.0, abs=1e-9)

    def test_known_rmse_and_mae(self) -> None:
        y_true = pd.Series([1.0, 2.0, 3.0])
        y_pred = np.array([2.0, 2.0, 2.0])
        metrics = regression_metrics(y_true, y_pred)
        assert metrics["mae"] == pytest.approx(2 / 3)
        assert metrics["rmse"] == pytest.approx((2 / 3) ** 0.5)


class TestQlikeLoss:
    def test_matches_hand_computed_value(self) -> None:
        # true_var=4, pred_var=1, ratio=4 -> 4 - ln(4) - 1
        y_true = pd.Series([2.0])
        y_pred = np.array([1.0])
        expected = 4.0 - np.log(4.0) - 1.0
        assert qlike_loss(y_true, y_pred) == pytest.approx(expected)

    def test_zero_for_perfect_prediction(self) -> None:
        y_true = pd.Series([0.5, 1.5, 3.0])
        assert qlike_loss(y_true, y_true.to_numpy()) == pytest.approx(0.0, abs=1e-9)

    def test_penalizes_underprediction_more_than_overprediction(self) -> None:
        # QLIKE's defining asymmetry: missing a spike (underpredicting) costs
        # more than overpredicting by the same absolute amount.
        y_true = pd.Series([2.0])
        underprediction = qlike_loss(y_true, np.array([1.0]))  # predicted half of actual
        overprediction = qlike_loss(y_true, np.array([4.0]))  # predicted double actual
        assert underprediction > overprediction

    def test_handles_non_positive_predictions_without_erroring(self) -> None:
        y_true = pd.Series([1.0, 2.0])
        y_pred = np.array([-0.5, 0.0])
        result = qlike_loss(y_true, y_pred)
        assert np.isfinite(result)


class TestTimeSeriesCvScores:
    def test_raises_when_too_few_rows(self) -> None:
        features = pd.DataFrame({"x": range(4)})
        target = pd.Series(range(4), dtype=float)
        with pytest.raises(InsufficientDataError):
            time_series_cv_scores(LinearRegression(), features, target, n_splits=5)

    def test_recovers_a_near_perfect_linear_relationship(self) -> None:
        rng = np.random.default_rng(0)
        x = np.arange(200, dtype=float)
        y = 3.0 * x + 1.0 + rng.normal(0, 1e-6, size=200)
        features = pd.DataFrame({"x": x})
        target = pd.Series(y)

        scores = time_series_cv_scores(LinearRegression(), features, target, n_splits=5)

        assert scores["r2"] == pytest.approx(1.0, abs=1e-4)
        assert set(scores.keys()) == {"rmse", "mae", "r2", "qlike"}
