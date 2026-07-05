"""Centralized, typed application configuration.

All environment variables are read exactly once, here, and validated by
pydantic. Every other module imports the `settings` singleton instead of
calling `os.getenv` directly — this gives us one place to see every
config knob the app has, and fails fast at startup if something required
is missing or malformed, rather than failing deep inside a service call.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- MongoDB ---
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "volatility_platform"

    # --- Data provider ---
    default_tickers: str = "AAPL,MSFT,GOOGL,AMZN,TSLA"
    ohlcv_lookback_days: int = 730

    # --- ML / model registry ---
    model_store_path: str = "./models_store"
    model_name: str = "volatility_predictor"
    # "filesystem" for local dev/tests (no MongoDB needed); "mongodb" for
    # production, since container disks on platforms like Render/Railway
    # don't reliably persist across redeploys without a paid disk add-on.
    model_registry_backend: str = "filesystem"

    # --- API ---
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"
    environment: str = Field(default="development")
    # Comma-separated allowed CORS origins for the frontend (e.g. the deployed
    # Vercel URL in production). The browser calls this API directly from
    # client components, so without CORS those requests would be rejected.
    cors_origins: str = "http://localhost:3000"

    @property
    def default_tickers_list(self) -> list[str]:
        """Parsed ticker list, e.g. 'AAPL,MSFT' -> ['AAPL', 'MSFT']."""
        return [t.strip().upper() for t in self.default_tickers.split(",") if t.strip()]

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (singleton within the process)."""
    return Settings()


settings = get_settings()
