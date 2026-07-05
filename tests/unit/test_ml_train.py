import pandas as pd
import pytest

from volatility_platform.domain.exceptions import InsufficientDataError
from volatility_platform.features.pipeline import build_feature_frame
from volatility_platform.ml.train import CANDIDATE_MODELS, select_best_model, train_model

from ..conftest import synthetic_ohlcv


def _feature_frame(n_days: int = 150) -> pd.DataFrame:
    return build_feature_frame(synthetic_ohlcv(n_days=n_days), horizon=5)


class TestSelectBestModel:
    def test_raises_when_not_enough_rows(self) -> None:
        small_frame = _feature_frame(n_days=70)  # yields fewer than MIN_TRAINING_ROWS after dropna
        with pytest.raises(InsufficientDataError):
            select_best_model(small_frame)

    def test_returns_a_valid_candidate_name_and_all_scores(self) -> None:
        frame = _feature_frame(n_days=150)
        best_name, all_scores = select_best_model(frame)

        assert best_name in CANDIDATE_MODELS
        assert set(all_scores.keys()) == set(CANDIDATE_MODELS.keys())
        for scores in all_scores.values():
            assert set(scores.keys()) == {"rmse", "mae", "r2"}


class TestTrainModel:
    def test_produces_fitted_model_and_matching_metadata(self) -> None:
        frame = _feature_frame(n_days=150)
        model, metadata = train_model(frame, model_name="volatility_predictor", horizon_days=5)

        expected_features = tuple(c for c in frame.columns if c != "target")
        assert metadata.name == "volatility_predictor"
        assert metadata.horizon_days == 5
        assert metadata.feature_names == expected_features
        assert metadata.training_samples == len(frame)
        assert metadata.algorithm in CANDIDATE_MODELS

        # The fitted model must actually be usable for inference on the same columns.
        prediction = model.predict(frame[list(expected_features)].iloc[[-1]])
        assert prediction.shape == (1,)

    def test_candidate_metrics_covers_every_model_and_matches_the_winner(self) -> None:
        frame = _feature_frame(n_days=150)
        _, metadata = train_model(frame, model_name="volatility_predictor", horizon_days=5)

        assert set(metadata.candidate_metrics.keys()) == set(CANDIDATE_MODELS.keys())
        for scores in metadata.candidate_metrics.values():
            assert set(scores.keys()) == {"rmse", "mae", "r2"}

        # The winning algorithm's entry in candidate_metrics must be the same
        # scores recorded as the model's own `metrics` -- one source of truth.
        assert metadata.candidate_metrics[metadata.algorithm] == metadata.metrics

        # And it must actually be the lowest-RMSE candidate, not just present.
        best_by_rmse = min(
            metadata.candidate_metrics, key=lambda name: metadata.candidate_metrics[name]["rmse"]
        )
        assert metadata.algorithm == best_by_rmse
