"""CLI entrypoint for (re)training the shared pooled volatility model.

Run manually or as a scheduled job — kept separate from `POST /train`
because training is CPU/memory-heavy (cross-validating three candidate
models across every configured ticker's pooled history), and shouldn't
run synchronously inside a resource-constrained API request/response
cycle. This matters concretely on free-tier hosting: a slow training
run can exceed the platform's reverse-proxy request timeout or the
instance's memory limit long before it exceeds any timeout we control
in application code.

Uses whichever model registry backend is configured (`MODEL_REGISTRY_BACKEND`)
— run with that set to `mongodb` to train locally (fast, unconstrained
hardware) while writing the result to the same MongoDB the deployed API
reads from, entirely sidestepping the deployed instance's resource limits.
"""

import asyncio
import logging

from volatility_platform.config.settings import settings
from volatility_platform.domain.models import Ticker
from volatility_platform.ml.registry import get_model_registry
from volatility_platform.repositories.mongo_client import close_client, get_database
from volatility_platform.repositories.price_repository import PriceRepository
from volatility_platform.services.training_service import TrainingService

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


async def main() -> None:
    database = get_database()
    price_repository = PriceRepository(database)
    model_registry = get_model_registry()

    tickers = [Ticker(symbol) for symbol in settings.default_tickers_list]
    service = TrainingService(price_repository, model_registry)

    metadata = await service.train_pooled_model(
        tickers, model_name=settings.model_name, horizon_days=5
    )
    logger.info(
        "Trained %s v%s (%s): %d samples, rmse=%.4f",
        metadata.name,
        metadata.version,
        metadata.algorithm,
        metadata.training_samples,
        metadata.metrics["rmse"],
    )

    await close_client()


if __name__ == "__main__":
    asyncio.run(main())
