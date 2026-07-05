"""Tests for MongoModelRegistry against an in-memory MongoDB mock (mongomock-motor).

Mirrors `tests/unit/test_ml_registry.py` (the filesystem backend) with the
same scenarios, since both must satisfy `ModelRegistryProtocol` identically.
"""

from datetime import UTC, datetime

import pytest
from mongomock_motor import AsyncMongoMockClient
from sklearn.linear_model import LinearRegression

from volatility_platform.domain.exceptions import ModelNotFoundError
from volatility_platform.domain.models import ModelMetadata
from volatility_platform.repositories.model_repository import MongoModelRegistry


@pytest.fixture
def model_registry() -> MongoModelRegistry:
    database = AsyncMongoMockClient()["test_db"]
    return MongoModelRegistry(database)


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


class TestMongoModelRegistry:
    async def test_round_trips_model_and_metadata(self, model_registry: MongoModelRegistry) -> None:
        model = LinearRegression().fit([[1.0], [2.0], [3.0]], [1.0, 2.0, 3.0])
        metadata = _sample_metadata()

        await model_registry.save_model(model, metadata)
        loaded_model, loaded_metadata = await model_registry.load_model("volatility_predictor")

        assert loaded_metadata == metadata
        assert loaded_model.predict([[4.0]])[0] == pytest.approx(4.0)

    async def test_get_latest_version_picks_newest_by_version_string(
        self, model_registry: MongoModelRegistry
    ) -> None:
        model = LinearRegression().fit([[1.0], [2.0]], [1.0, 2.0])
        await model_registry.save_model(model, _sample_metadata(version="20260101_000000"))
        await model_registry.save_model(model, _sample_metadata(version="20260705_120000"))

        assert await model_registry.get_latest_version("volatility_predictor") == "20260705_120000"

    async def test_load_missing_model_raises(self, model_registry: MongoModelRegistry) -> None:
        with pytest.raises(ModelNotFoundError):
            await model_registry.load_model("nonexistent_model")

    async def test_list_versions_returns_most_recent_first(
        self, model_registry: MongoModelRegistry
    ) -> None:
        model = LinearRegression().fit([[1.0], [2.0]], [1.0, 2.0])
        await model_registry.save_model(model, _sample_metadata(version="20260101_000000"))
        await model_registry.save_model(model, _sample_metadata(version="20260705_120000"))

        versions = await model_registry.list_versions("volatility_predictor")
        assert versions == ["20260705_120000", "20260101_000000"]
