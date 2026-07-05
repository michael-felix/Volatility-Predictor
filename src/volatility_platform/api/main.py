"""FastAPI application entrypoint.

Wires together lifespan startup/shutdown (MongoDB connection, index
creation), domain-exception -> HTTP status code translation, the
Prometheus metrics middleware, and the route modules under `api/routers/`.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from volatility_platform.api.middleware import PrometheusMiddleware
from volatility_platform.api.routers import health, predictions, tickers, training
from volatility_platform.config.settings import settings
from volatility_platform.domain.exceptions import (
    DataProviderError,
    DataValidationError,
    InsufficientDataError,
    ModelNotFoundError,
    TickerNotFoundError,
)
from volatility_platform.repositories.mongo_client import close_client, get_database
from volatility_platform.repositories.prediction_repository import PredictionRepository
from volatility_platform.repositories.price_repository import PriceRepository

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

_EXCEPTION_STATUS_CODES: dict[type[Exception], int] = {
    TickerNotFoundError: 404,
    ModelNotFoundError: 404,
    DataValidationError: 422,
    InsufficientDataError: 422,
    DataProviderError: 502,
}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Index creation failing shouldn't prevent the app from starting: a
    # `/health` check reporting "degraded" is only possible if the process
    # actually comes up, and an unreachable database at boot time (e.g. a
    # transient network blip during deploy) shouldn't be a hard crash when
    # it might recover a moment later.
    try:
        database = get_database()
        await PriceRepository(database).ensure_indexes()
        await PredictionRepository(database).ensure_indexes()

        if settings.model_registry_backend == "mongodb":
            from volatility_platform.repositories.model_repository import MongoModelRegistry

            await MongoModelRegistry(database).ensure_indexes()
        logger.info("Startup complete: MongoDB indexes ensured")
    except Exception:
        logger.exception("Could not ensure MongoDB indexes at startup; continuing anyway")

    yield
    await close_client()
    logger.info("Shutdown complete: MongoDB connection closed")


app = FastAPI(
    title="Stock Volatility Prediction Platform",
    description="Real-time stock volatility forecasting API.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(PrometheusMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(tickers.router)
app.include_router(predictions.router)
app.include_router(training.router)


def _domain_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    status_code = _EXCEPTION_STATUS_CODES.get(type(exc), 500)
    return JSONResponse(status_code=status_code, content={"detail": str(exc)})


for _exc_type in _EXCEPTION_STATUS_CODES:
    app.add_exception_handler(_exc_type, _domain_exception_handler)
