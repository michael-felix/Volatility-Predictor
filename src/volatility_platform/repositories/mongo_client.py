"""Shared MongoDB connection.

A single `AsyncIOMotorClient` is created lazily and cached for the life
of the process — constructing a new client per request/repository would
exhaust the connection pool under load. Motor's client construction
itself doesn't block on a network round-trip (the actual TCP connection
happens lazily on first use), so `get_database()` is safe to call from
synchronous code paths too, such as `ml.registry.get_model_registry()`.
"""

from functools import lru_cache
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from volatility_platform.config.settings import settings


@lru_cache
def get_client() -> AsyncIOMotorClient[dict[str, Any]]:
    # A short server-selection timeout means an unreachable MongoDB fails
    # fast (seconds, not the 30s default) — this matters for both the
    # `/health` check and app startup: neither should hang for half a
    # minute just to discover the database is down.
    return AsyncIOMotorClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)


def get_database() -> AsyncIOMotorDatabase[dict[str, Any]]:
    return get_client()[settings.mongodb_db_name]


async def close_client() -> None:
    """Close the Mongo client. Call this during FastAPI application shutdown."""
    get_client().close()
    get_client.cache_clear()
