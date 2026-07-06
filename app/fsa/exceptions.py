class FsaConfigurationError(Exception):
    """Raised when FSA client is missing required configuration."""


class FsaApiError(Exception):
    """Raised when a request to the FSA registry fails or returns an unexpected payload."""


class FsaRateLimitedError(FsaApiError):
    """Raised when the caller would have to wait longer than the allowed maximum for a free slot."""


class FsaCircuitOpenError(FsaApiError):
    """Raised when the circuit breaker is open and the call is short-circuited."""
