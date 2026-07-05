from datetime import UTC, datetime
from pathlib import Path

import pytest
from sklearn.linear_model import LinearRegression

from volatility_platform.domain.exceptions import ModelNotFoundError
from volatility_platform.domain.models import ModelMetadata
from volatility_platform.ml.registry import FileSystemModelRegistry


def _sample_metadata(version: str = "20260705_120000") -> ModelMetadata:
    return ModelMetadata(
        name="volatility_predictor",
        version=version,
        algorithm="linear_regression",
        horizon_days=5,
        trained_at=datetime(2026, 7, 5, 12, 0, 0, tzinfo=UTC),
        feature_names=("log_return", "rv_daily"),
        metrics={"rmse": 0.01, "mae": 0.008, "r2": 0.5},
        hyperparameters={"fit_intercept": True},
        training_samples=100,
    )


@pytest.fixture
def registry(tmp_path: Path) -> FileSystemModelRegistry:
    return FileSystemModelRegistry(store_path=str(tmp_path))


class TestFileSystemModelRegistry:
    async def test_round_trips_model_and_metadata(self, registry: FileSystemModelRegistry) -> None:
        model = LinearRegression().fit([[1.0], [2.0], [3.0]], [1.0, 2.0, 3.0])
        metadata = _sample_metadata()

        await registry.save_model(model, metadata)
        loaded_model, loaded_metadata = await registry.load_model("volatility_predictor")

        assert loaded_metadata == metadata
        assert loaded_model.predict([[4.0]])[0] == pytest.approx(4.0)

    async def test_latest_pointer_advances_to_newest_version(
        self, registry: FileSystemModelRegistry
    ) -> None:
        model = LinearRegression().fit([[1.0], [2.0]], [1.0, 2.0])
        await registry.save_model(model, _sample_metadata(version="20260101_000000"))
        await registry.save_model(model, _sample_metadata(version="20260705_120000"))

        assert await registry.get_latest_version("volatility_predictor") == "20260705_120000"

    async def test_load_specific_version(self, registry: FileSystemModelRegistry) -> None:
        model = LinearRegression().fit([[1.0], [2.0]], [1.0, 2.0])
        await registry.save_model(model, _sample_metadata(version="20260101_000000"))
        await registry.save_model(model, _sample_metadata(version="20260705_120000"))

        _, metadata = await registry.load_model("volatility_predictor", version="20260101_000000")
        assert metadata.version == "20260101_000000"

    async def test_load_missing_model_raises(self, registry: FileSystemModelRegistry) -> None:
        with pytest.raises(ModelNotFoundError):
            await registry.load_model("nonexistent_model")

    async def test_list_versions_returns_most_recent_first(
        self, registry: FileSystemModelRegistry
    ) -> None:
        model = LinearRegression().fit([[1.0], [2.0]], [1.0, 2.0])
        await registry.save_model(model, _sample_metadata(version="20260101_000000"))
        await registry.save_model(model, _sample_metadata(version="20260705_120000"))

        versions = await registry.list_versions("volatility_predictor")
        assert versions == ["20260705_120000", "20260101_000000"]

    async def test_list_versions_empty_for_unknown_model(
        self, registry: FileSystemModelRegistry
    ) -> None:
        assert await registry.list_versions("nonexistent_model") == []
