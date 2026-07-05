"""MongoDB-backed model registry — the production backend for storing
trained model artifacts.

Container filesystems on platforms like Render/Railway are typically
ephemeral, so a model saved via `ml.registry.FileSystemModelRegistry`
can vanish on the next redeploy or restart. Storing the serialized model
in MongoDB alongside its metadata means the API only ever needs one
external dependency (the database it already talks to) to recover its
trained model after a restart — no persistent disk add-on required.

Model binaries here (RandomForest/GradientBoosting over a small feature
set) are small enough — a few hundred KB to low single-digit MB — to
store as plain BSON binary in a document; GridFS would only be needed
for artifacts approaching MongoDB's 16MB document size limit.
"""

from __future__ import annotations

import io
from typing import Any

import joblib
from bson.binary import Binary
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import DESCENDING, IndexModel
from sklearn.base import BaseEstimator

from volatility_platform.domain.exceptions import ModelNotFoundError
from volatility_platform.domain.models import ModelMetadata
from volatility_platform.ml.registry import metadata_from_dict, metadata_to_dict

COLLECTION_NAME = "models"


class MongoModelRegistry:
    """Stores trained model artifacts + metadata as documents in the `models` collection.

    Implements the same `ml.registry.ModelRegistryProtocol` as
    `FileSystemModelRegistry`, so services and API routes can use
    whichever backend is active without any code change.
    """

    def __init__(self, database: AsyncIOMotorDatabase[dict[str, Any]]) -> None:
        self._collection = database[COLLECTION_NAME]

    async def ensure_indexes(self) -> None:
        await self._collection.create_indexes(
            [IndexModel([("name", 1), ("version", DESCENDING)], unique=True)]
        )

    async def save_model(self, model: BaseEstimator, metadata: ModelMetadata) -> None:
        buffer = io.BytesIO()
        joblib.dump(model, buffer)

        document: dict[str, Any] = metadata_to_dict(metadata)
        document["model_bytes"] = Binary(buffer.getvalue())
        await self._collection.update_one(
            {"name": metadata.name, "version": metadata.version},
            {"$set": document},
            upsert=True,
        )

    async def load_model(
        self, model_name: str, version: str = "latest"
    ) -> tuple[BaseEstimator, ModelMetadata]:
        resolved = await self.get_latest_version(model_name) if version == "latest" else version
        doc = await self._collection.find_one({"name": model_name, "version": resolved})
        if doc is None:
            raise ModelNotFoundError(f"No model found for name={model_name!r} version={resolved!r}")
        model = joblib.load(io.BytesIO(doc["model_bytes"]))
        metadata = metadata_from_dict(doc)
        return model, metadata

    async def get_latest_version(self, model_name: str) -> str:
        # Version strings are "%Y%m%d_%H%M%S" timestamps, so lexicographic
        # sort order matches chronological order.
        doc = await self._collection.find_one({"name": model_name}, sort=[("version", DESCENDING)])
        if doc is None:
            raise ModelNotFoundError(f"No trained model found for name={model_name!r}")
        return str(doc["version"])

    async def list_versions(self, model_name: str) -> list[str]:
        cursor = self._collection.find({"name": model_name}, {"version": 1}).sort(
            "version", DESCENDING
        )
        documents = await cursor.to_list(length=None)
        return [doc["version"] for doc in documents]
