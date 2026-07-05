"""End-to-end API tests via `httpx.AsyncClient` against the ASGI app directly
(no real network, no real MongoDB, no real yfinance).

`repositories.mongo_client.get_client` is monkeypatched to return an
in-memory `AsyncMongoMockClient`, which both the app's lifespan and every
`Depends(get_database)` route dependency resolve through — a single patch
point rather than patching each callsite separately. The model registry
is overridden via FastAPI's `dependency_overrides` (the intended mechanism
for `Depends`-injected dependencies) to a `FileSystemModelRegistry` rooted
at a temp directory, so tests never touch the real `models_store/`.
"""

from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
from mongomock_motor import AsyncMongoMockClient

import volatility_platform.repositories.mongo_client as mongo_client_module
from volatility_platform.api.dependencies import get_model_registry_dependency
from volatility_platform.api.main import app
from volatility_platform.domain.models import OHLCVBar, Ticker
from volatility_platform.ml.registry import FileSystemModelRegistry
from volatility_platform.ml.train import CANDIDATE_MODELS
from volatility_platform.repositories.price_repository import PriceRepository

from ..conftest import synthetic_ohlcv


@pytest.fixture
async def client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[httpx.AsyncClient]:
    mock_client = AsyncMongoMockClient()
    monkeypatch.setattr(mongo_client_module, "get_client", lambda: mock_client)

    registry = FileSystemModelRegistry(store_path=str(tmp_path))
    app.dependency_overrides[get_model_registry_dependency] = lambda: registry

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client

    app.dependency_overrides.clear()


async def _seed_ticker(symbol: str, n_days: int = 150, seed: int = 1) -> Ticker:
    database = mongo_client_module.get_client()[mongo_client_module.settings.mongodb_db_name]
    repository = PriceRepository(database)
    ticker = Ticker(symbol)
    ohlcv = synthetic_ohlcv(n_days=n_days, seed=seed)
    bars = [
        OHLCVBar(
            ticker,
            idx.date(),
            row["open"],
            row["high"],
            row["low"],
            row["close"],
            int(row["volume"]),
        )
        for idx, row in ohlcv.iterrows()
    ]
    await repository.upsert_bars(bars)
    return ticker


class TestHealthAndRoot:
    async def test_root(self, client: httpx.AsyncClient) -> None:
        response = await client.get("/")
        assert response.status_code == 200
        assert "docs" in response.json()

    async def test_health(self, client: httpx.AsyncClient) -> None:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["mongodb_connected"] is True

    async def test_metrics_exposes_prometheus_format(self, client: httpx.AsyncClient) -> None:
        await client.get("/health")  # generate at least one request metric
        response = await client.get("/metrics")
        assert response.status_code == 200
        assert "http_requests_total" in response.text


class TestTickers:
    async def test_list_tickers_before_ingestion(self, client: httpx.AsyncClient) -> None:
        response = await client.get("/tickers")
        assert response.status_code == 200
        body = response.json()
        assert len(body) > 0
        assert all(item["bar_count"] == 0 for item in body)

    async def test_list_tickers_reflects_stored_data(self, client: httpx.AsyncClient) -> None:
        await _seed_ticker("AAPL", n_days=150)
        response = await client.get("/tickers")
        body = response.json()
        aapl = next(item for item in body if item["ticker"] == "AAPL")
        assert aapl["bar_count"] == 150
        assert aapl["latest_trading_date"] is not None


class TestTrainingAndPrediction:
    async def test_train_then_predict_end_to_end(self, client: httpx.AsyncClient) -> None:
        await _seed_ticker("AAPL", n_days=150, seed=1)

        train_response = await client.post("/train", json={"tickers": ["AAPL"], "horizon_days": 5})
        assert train_response.status_code == 200
        train_body = train_response.json()
        assert train_body["training_samples"] > 0
        assert train_body["algorithm"] in train_body["candidate_metrics"]
        assert set(train_body["candidate_metrics"].keys()) == set(CANDIDATE_MODELS.keys())

        predict_response = await client.post("/predict", json={"ticker": "AAPL"})
        assert predict_response.status_code == 200
        predict_body = predict_response.json()
        assert predict_body["ticker"] == "AAPL"
        assert predict_body["predicted_volatility"] >= 0.0
        assert predict_body["annualized_volatility_pct"] >= 0.0
        assert predict_body["current_price"] > 0

        history_response = await client.get("/predictions/AAPL")
        assert history_response.status_code == 200
        assert len(history_response.json()) == 1

        info_response = await client.get("/model-info")
        assert info_response.status_code == 200
        info_body = info_response.json()
        assert info_body["model_name"] == train_body["model_name"]
        assert set(info_body["candidate_metrics"].keys()) == set(CANDIDATE_MODELS.keys())

    async def test_predict_without_stored_history_returns_404(
        self, client: httpx.AsyncClient
    ) -> None:
        response = await client.post("/predict", json={"ticker": "NVDA"})
        assert response.status_code == 404

    async def test_predict_without_trained_model_returns_404(
        self, client: httpx.AsyncClient
    ) -> None:
        await _seed_ticker("AAPL", n_days=150, seed=1)
        response = await client.post("/predict", json={"ticker": "AAPL"})
        assert response.status_code == 404

    async def test_train_with_invalid_ticker_symbol_returns_422(
        self, client: httpx.AsyncClient
    ) -> None:
        response = await client.post("/train", json={"tickers": ["!!!"]})
        assert response.status_code == 422
