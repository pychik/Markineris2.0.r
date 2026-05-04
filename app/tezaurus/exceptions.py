class TezaurusError(Exception):
    """Base exception for Tezaurus module errors."""


class TezaurusConfigurationError(TezaurusError):
    """Raised when Tezaurus integration config is invalid or incomplete."""


class TezaurusApiError(TezaurusError):
    """Raised when remote Tezaurus API request fails."""


class TezaurusStorageError(TezaurusError):
    """Raised when Redis storage payload cannot be processed."""
