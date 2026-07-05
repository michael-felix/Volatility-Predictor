"""POST /predict and GET /predictions/{ticker} — inference and prediction history."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from volatility_platform.api.dependencies import get_prediction_service
from volatility_platform.api.schemas import PredictionRequest, PredictionResponse
from volatility_platform.config.settings import settings
from volatility_platform.domain.models import Ticker
from volatility_platform.services.prediction_service import PredictionService

router = APIRouter(tags=["predictions"])

PredictionServiceDep = Annotated[PredictionService, Depends(get_prediction_service)]


@router.post(
    "/predict", response_model=PredictionResponse, summary="Predict volatility for a ticker"
)
async def predict(request: PredictionRequest, service: PredictionServiceDep) -> PredictionResponse:
    ticker = Ticker(request.ticker)
    model_name = request.model_name or settings.model_name
    prediction = await service.predict(ticker, model_name=model_name)
    return PredictionResponse.from_domain(prediction)


@router.get(
    "/predictions/{ticker}",
    response_model=list[PredictionResponse],
    summary="Prediction history for a ticker",
)
async def get_prediction_history(
    ticker: str,
    service: PredictionServiceDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[PredictionResponse]:
    predictions = await service.get_prediction_history(Ticker(ticker), limit=limit)
    return [PredictionResponse.from_domain(p) for p in predictions]
