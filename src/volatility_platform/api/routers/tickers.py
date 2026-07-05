"""GET /tickers — configured tickers and their stored-data status."""

from __future__ import annotations

from fastapi import APIRouter

from volatility_platform.api.dependencies import PriceRepositoryDep
from volatility_platform.api.schemas import TickerInfo
from volatility_platform.config.settings import settings
from volatility_platform.domain.models import Ticker

router = APIRouter(tags=["tickers"])


@router.get("/tickers", response_model=list[TickerInfo], summary="List configured tickers")
async def list_tickers(price_repository: PriceRepositoryDep) -> list[TickerInfo]:
    results = []
    for symbol in settings.default_tickers_list:
        ticker = Ticker(symbol)
        latest_date = await price_repository.get_latest_date(ticker)
        bar_count = await price_repository.count_bars(ticker)
        results.append(
            TickerInfo(ticker=symbol, latest_trading_date=latest_date, bar_count=bar_count)
        )
    return results
