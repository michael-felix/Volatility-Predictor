"""Root, health-check, and Prometheus metrics endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from volatility_platform.api.schemas import HealthResponse
from volatility_platform.repositories.mongo_client import get_database

router = APIRouter(tags=["health"])


@router.get("/", summary="API root")
async def root() -> dict[str, str]:
    return {"name": "Stock Volatility Prediction Platform", "docs": "/docs"}


@router.get("/health", response_model=HealthResponse, summary="Health check")
async def health_check() -> HealthResponse:
    try:
        await get_database().command("ping")
        mongodb_connected = True
    except Exception:
        mongodb_connected = False
    return HealthResponse(
        status="ok" if mongodb_connected else "degraded", mongodb_connected=mongodb_connected
    )


@router.get("/metrics", summary="Prometheus metrics")
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
