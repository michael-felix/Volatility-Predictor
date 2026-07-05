"""MongoDB-backed repository for volatility predictions (prediction history).

Every prediction the API serves is persisted here, which is what powers
a prediction-history view on the dashboard and lets us later evaluate
predicted vs. actual volatility once enough time has passed.
"""

from __future__ import annotations

from datetime import UTC, date
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, IndexModel

from volatility_platform.domain.models import Ticker, VolatilityPrediction

COLLECTION_NAME = "predictions"


class PredictionRepository:
    """Stores and retrieves volatility predictions."""

    def __init__(self, database: AsyncIOMotorDatabase[dict[str, Any]]) -> None:
        self._collection = database[COLLECTION_NAME]

    async def ensure_indexes(self) -> None:
        await self._collection.create_indexes(
            [IndexModel([("ticker", ASCENDING), ("generated_at", DESCENDING)])]
        )

    async def save_prediction(self, prediction: VolatilityPrediction) -> None:
        await self._collection.insert_one(
            {
                "ticker": prediction.ticker.symbol,
                "horizon_days": prediction.horizon_days,
                "predicted_volatility": prediction.predicted_volatility,
                "current_price": prediction.current_price,
                "model_name": prediction.model_name,
                "model_version": prediction.model_version,
                "as_of_date": prediction.as_of_date.isoformat(),
                "generated_at": prediction.generated_at,
            }
        )

    async def get_predictions(self, ticker: Ticker, limit: int = 50) -> list[VolatilityPrediction]:
        """Most recent predictions for `ticker`, newest first.

        Sorts by `generated_at` with `_id` as a tie-breaker: BSON
        datetimes are millisecond-precision, so predictions saved within
        the same millisecond (e.g. a batch job scoring several tickers
        back-to-back) would otherwise have no guaranteed relative order.
        `_id` is monotonically increasing on insert, so it recovers the
        true insertion order for any tied `generated_at` values.
        """
        cursor = (
            self._collection.find({"ticker": ticker.symbol})
            .sort([("generated_at", DESCENDING), ("_id", DESCENDING)])
            .limit(limit)
        )
        documents = await cursor.to_list(length=limit)
        return [self._to_domain(doc, ticker) for doc in documents]

    @staticmethod
    def _to_domain(doc: dict[str, Any], ticker: Ticker) -> VolatilityPrediction:
        generated_at = doc["generated_at"]
        if generated_at.tzinfo is None:
            generated_at = generated_at.replace(tzinfo=UTC)
        return VolatilityPrediction(
            ticker=ticker,
            horizon_days=doc["horizon_days"],
            predicted_volatility=doc["predicted_volatility"],
            current_price=doc["current_price"],
            model_name=doc["model_name"],
            model_version=doc["model_version"],
            as_of_date=date.fromisoformat(doc["as_of_date"]),
            generated_at=generated_at,
        )
