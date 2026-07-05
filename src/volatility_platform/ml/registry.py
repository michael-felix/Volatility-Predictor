"""Model registry: an async interface with two interchangeable backends.

- `FileSystemModelRegistry`: joblib artifact + JSON metadata sidecar on
  local disk. Fast, no external service required — used for local
  development and unit tests.
- `repositories.model_repository.MongoModelRegistry`: model bytes +
  metadata stored as a MongoDB document. This is the production
  backend, because container filesystems on platforms like Render/
  Railway are typically ephemeral — a model saved to local disk can
  vanish on the next redeploy or restart unless a paid persistent disk
  is attached.

Both backends implement `ModelRegistryProtocol`, so callers (services,
API routes, training scripts) depend only on the interface and never
need to know which backend is active — that's decided once, via
`get_model_registry()`, based on `settings.model_registry_backend`.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

import joblib
from sklearn.base import BaseEstimator

from volatility_platform.config.settings import settings
from volatility_platform.domain.exceptions import ModelNotFoundError
from volatility_platform.domain.models import ModelMetadata


class ModelRegistryProtocol(Protocol):
    """Contract both the filesystem and MongoDB model registries satisfy."""

    async def save_model(self, model: BaseEstimator, metadata: ModelMetadata) -> None: ...

    async def load_model(
        self, model_name: str, version: str = "latest"
    ) -> tuple[BaseEstimator, ModelMetadata]: ...

    async def get_latest_version(self, model_name: str) -> str: ...

    async def list_versions(self, model_name: str) -> list[str]: ...


def metadata_to_dict(metadata: ModelMetadata) -> dict[str, Any]:
    """Serialize `ModelMetadata` to a JSON/BSON-friendly dict. Shared by both backends
    so the on-disk and in-Mongo representations never drift apart."""
    data = asdict(metadata)
    data["trained_at"] = metadata.trained_at.isoformat()
    data["feature_names"] = list(metadata.feature_names)
    return data


def metadata_from_dict(data: dict[str, Any]) -> ModelMetadata:
    """Inverse of `metadata_to_dict`."""
    return ModelMetadata(
        name=data["name"],
        version=data["version"],
        algorithm=data["algorithm"],
        horizon_days=data["horizon_days"],
        trained_at=datetime.fromisoformat(data["trained_at"]),
        feature_names=tuple(data["feature_names"]),
        metrics=data["metrics"],
        hyperparameters=data["hyperparameters"],
        training_samples=data["training_samples"],
    )


class FileSystemModelRegistry:
    """Local-disk model registry: one joblib artifact + JSON metadata sidecar per
    version, plus a plain-text 'latest' pointer file per model name.

    Storage layout:
        {store_path}/{model_name}/{version}/model.joblib
        {store_path}/{model_name}/{version}/metadata.json
        {store_path}/{model_name}/latest.txt
    """

    def __init__(self, store_path: str | None = None) -> None:
        self._store_path = Path(store_path or settings.model_store_path)

    def _model_root(self, model_name: str) -> Path:
        return self._store_path / model_name

    def _version_dir(self, model_name: str, version: str) -> Path:
        return self._model_root(model_name) / version

    async def save_model(self, model: BaseEstimator, metadata: ModelMetadata) -> None:
        # Local file writes are small and fast enough that running them directly
        # (rather than off the event loop via asyncio.to_thread) is an acceptable
        # tradeoff for this backend's use case: local dev and unit tests.
        version_dir = self._version_dir(metadata.name, metadata.version)
        version_dir.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, version_dir / "model.joblib")
        (version_dir / "metadata.json").write_text(
            json.dumps(metadata_to_dict(metadata), indent=2, default=str)
        )
        (self._model_root(metadata.name) / "latest.txt").write_text(metadata.version)

    async def load_model(
        self, model_name: str, version: str = "latest"
    ) -> tuple[BaseEstimator, ModelMetadata]:
        resolved = await self.get_latest_version(model_name) if version == "latest" else version
        version_dir = self._version_dir(model_name, resolved)
        model_path = version_dir / "model.joblib"
        metadata_path = version_dir / "metadata.json"
        if not model_path.exists() or not metadata_path.exists():
            raise ModelNotFoundError(f"No model found for name={model_name!r} version={resolved!r}")
        model = joblib.load(model_path)
        metadata = metadata_from_dict(json.loads(metadata_path.read_text()))
        return model, metadata

    async def get_latest_version(self, model_name: str) -> str:
        pointer = self._model_root(model_name) / "latest.txt"
        if not pointer.exists():
            raise ModelNotFoundError(f"No trained model found for name={model_name!r}")
        return pointer.read_text().strip()

    async def list_versions(self, model_name: str) -> list[str]:
        root = self._model_root(model_name)
        if not root.exists():
            return []
        return sorted((p.name for p in root.iterdir() if p.is_dir()), reverse=True)


def get_model_registry() -> ModelRegistryProtocol:
    """Return the active model registry backend, per `settings.model_registry_backend`.

    Imports the MongoDB backend lazily, inside the function body, to
    avoid a circular import: `repositories/model_repository.py` imports
    `metadata_to_dict`/`metadata_from_dict` from this module.
    """
    if settings.model_registry_backend == "mongodb":
        from volatility_platform.repositories.model_repository import MongoModelRegistry
        from volatility_platform.repositories.mongo_client import get_database

        return MongoModelRegistry(get_database())
    return FileSystemModelRegistry()
