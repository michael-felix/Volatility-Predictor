"""CLI entrypoint for scheduled daily OHLCV ingestion.

Run via `python pipelines/ingest_daily.py` — manually, or as a cron/scheduled
task in production — to pull the latest bars for every configured ticker
into MongoDB. Kept as a standalone script, separate from the request/response
API process, because ingestion has different timing and failure semantics
than a request (see `services/ingestion_service.py`): a failed fetch today
can just retry on the next scheduled run.
"""

import asyncio
import logging

from volatility_platform.config.settings import settings
from volatility_platform.data_providers.yfinance_provider import YFinanceProvider
from volatility_platform.domain.models import Ticker
from volatility_platform.repositories.mongo_client import close_client, get_database
from volatility_platform.repositories.price_repository import PriceRepository
from volatility_platform.services.ingestion_service import IngestionService

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


async def main() -> None:
    database = get_database()
    price_repository = PriceRepository(database)
    await price_repository.ensure_indexes()

    service = IngestionService(YFinanceProvider(), price_repository)
    tickers = [Ticker(symbol) for symbol in settings.default_tickers_list]

    results = await service.ingest_tickers(tickers, lookback_days=settings.ohlcv_lookback_days)
    for symbol, count in results.items():
        logger.info("Ingested %d bars for %s", count, symbol)

    await close_client()


if __name__ == "__main__":
    asyncio.run(main())
