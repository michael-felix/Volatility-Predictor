"""Domain-specific exceptions.

Raised by domain, feature, and ML code so that outer layers (API,
services) can catch specific failure modes and translate them into the
right HTTP status codes or retry behavior, instead of catching bare
`Exception` and losing information about what actually went wrong.
"""


class DomainError(Exception):
    """Base class for all domain-level errors."""


class DataValidationError(DomainError):
    """Raised when an OHLCV bar or other domain object fails validation."""


class InsufficientDataError(DomainError):
    """Raised when there isn't enough historical data to compute a feature or prediction."""


class TickerNotFoundError(DomainError):
    """Raised when a requested ticker has no data available."""


class ModelNotFoundError(DomainError):
    """Raised when no trained model artifact exists for the requested name/version."""


class DataProviderError(DomainError):
    """Raised when an external market data provider (e.g. yfinance) fails to return data."""
