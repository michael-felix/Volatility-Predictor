"""POST /train and GET /model-info — model training and inspection."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from volatility_platform.api.dependencies import ModelRegistryDep, get_training_service
from volatility_platform.api.schemas import ModelInfoResponse, TrainRequest, TrainResponse
from volatility_platform.config.settings import settings
from volatility_platform.domain.models import Ticker
from volatility_platform.services.training_service import TrainingService

router = APIRouter(tags=["training"])

TrainingServiceDep = Annotated[TrainingService, Depends(get_training_service)]


@router.post("/train", response_model=TrainResponse, summary="Train the pooled volatility model")
async def train(request: TrainRequest, service: TrainingServiceDep) -> TrainResponse:
    symbols = request.tickers or settings.default_tickers_list
    tickers = [Ticker(symbol) for symbol in symbols]
    metadata = await service.train_pooled_model(
        tickers, model_name=settings.model_name, horizon_days=request.horizon_days
    )
    return TrainResponse.from_domain(metadata)


@router.get(
    "/model-info", response_model=ModelInfoResponse, summary="Currently active model's metadata"
)
async def model_info(model_registry: ModelRegistryDep) -> ModelInfoResponse:
    _, metadata = await model_registry.load_model(settings.model_name)
    return ModelInfoResponse.from_domain(metadata)
