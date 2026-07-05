"""Dependency-injection wiring.

Constructs repositories and services from the shared MongoDB connection,
so route handlers only ever depend on service classes — never directly
on `AsyncIOMotorDatabase` or which model registry backend is active.
Swapping MongoDB for another database, or the model registry's backend,
means changing this file alone.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from volatility_platform.data_providers.yfinance_provider import YFinanceProvider
from volatility_platform.ml.registry import ModelRegistryProtocol, get_model_registry
from volatility_platform.repositories.mongo_client import get_database
from volatility_platform.repositories.prediction_repository import PredictionRepository
from volatility_platform.repositories.price_repository import PriceRepository
from volatility_platform.services.ingestion_service import IngestionService
from volatility_platform.services.prediction_service import PredictionService
from volatility_platform.services.training_service import TrainingService

Database = Annotated[AsyncIOMotorDatabase[dict[str, Any]], Depends(get_database)]


def get_price_repository(database: Database) -> PriceRepository:
    return PriceRepository(database)


def get_prediction_repository(database: Database) -> PredictionRepository:
    return PredictionRepository(database)


def get_model_registry_dependency() -> ModelRegistryProtocol:
    return get_model_registry()


PriceRepositoryDep = Annotated[PriceRepository, Depends(get_price_repository)]
PredictionRepositoryDep = Annotated[PredictionRepository, Depends(get_prediction_repository)]
ModelRegistryDep = Annotated[ModelRegistryProtocol, Depends(get_model_registry_dependency)]


def get_ingestion_service(price_repository: PriceRepositoryDep) -> IngestionService:
    return IngestionService(YFinanceProvider(), price_repository)


def get_prediction_service(
    price_repository: PriceRepositoryDep,
    prediction_repository: PredictionRepositoryDep,
    model_registry: ModelRegistryDep,
) -> PredictionService:
    return PredictionService(price_repository, prediction_repository, model_registry)


def get_training_service(
    price_repository: PriceRepositoryDep, model_registry: ModelRegistryDep
) -> TrainingService:
    return TrainingService(price_repository, model_registry)
