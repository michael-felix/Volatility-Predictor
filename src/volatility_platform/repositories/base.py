"""Shared repository contract.

Every Mongo-backed repository exposes `ensure_indexes()`, called once
during FastAPI startup, so index creation happens in one predictable
place rather than being scattered across ad hoc scripts.
"""

from typing import Protocol


class MongoRepository(Protocol):
    async def ensure_indexes(self) -> None: ...
