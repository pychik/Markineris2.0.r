from __future__ import annotations

from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import settings
from redis_queue.redis_instance import get_redis_client

from .circuit_breaker import RedisCircuitBreaker
from .constants import REDIS_KEY_CIRCUIT, REDIS_KEY_RATE_LIMIT, REDIS_KEY_TOKEN, REDIS_KEY_TOKEN_LOCK
from .exceptions import FsaApiError
from .rate_limiter import RedisRateLimiter
from .token_store import FsaTokenStore

_RETRY_STATUSES = (500, 502, 503, 504)


def _build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=1,
        status_forcelist=_RETRY_STATUSES,
        allowed_methods=frozenset(["GET", "POST"]),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


class BaseFsaClient:
    """Shared plumbing for FSA registry clients: token caching, global rate limiting and
    circuit breaking. Declaration and certificate clients hit the same host/IP-limited
    service, so they share one rate limiter and one circuit breaker instance."""

    def __init__(
        self,
        *,
        rate_limiter: RedisRateLimiter,
        circuit_breaker: RedisCircuitBreaker,
        token_store: FsaTokenStore,
    ) -> None:
        self.base_url = settings.FSA_BASE_URL.rstrip("/")
        self.timeout = settings.FSA_TIMEOUT
        self.rate_limiter = rate_limiter
        self.circuit_breaker = circuit_breaker
        self.token_store = token_store
        self.session = _build_session()

    def _login(self) -> str:
        response = self.session.post(
            f"{self.base_url}/login",
            json={
                "username": settings.FSA_LOGIN_USERNAME,
                "password": settings.FSA_LOGIN_PASSWORD,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()

        token = response.headers.get("Authorization")
        if not token:
            raise FsaApiError("Authorization header not found in /login response")

        return token

    def _headers(self) -> dict[str, str]:
        token = self.token_store.get_token(login_fn=self._login)
        return {
            "Authorization": token,
            "Content-Type": "application/json",
            "Accept": "application/json",
            # пустые в анонимном режиме, но реальный фронт ФСА всегда их отправляет
            "lkId": "",
            "orgId": "",
        }

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        self.circuit_breaker.before_call()
        self.rate_limiter.acquire()

        try:
            response = self.session.request(
                method,
                f"{self.base_url}{path}",
                headers=self._headers(),
                timeout=self.timeout,
                **kwargs,
            )

            if response.status_code == 429:
                self.circuit_breaker.on_failure()
                raise FsaApiError("ФСА вернул 429 (превышен лимит запросов)")

            response.raise_for_status()
        except requests.RequestException as exc:
            self.circuit_breaker.on_failure()
            raise FsaApiError(f"Ошибка запроса к ФСА {path}: {exc}") from exc
        except FsaApiError:
            raise
        else:
            self.circuit_breaker.on_success()
            return response


class FsaDeclarationClient(BaseFsaClient):
    def find_by_number(self, number: str) -> dict[str, Any] | None:
        payload = {
            "size": 10,
            "page": 0,
            "count": 0,
            "filter": {
                "columnsSearch": [{"name": "number", "search": number, "type": 0}],
                "number": number,
            },
        }

        response = self._request("POST", "/api/v1/rds/common/declarations/get", json=payload)
        items = response.json().get("items", [])
        return items[0] if items else None

    def get_card(self, declaration_id: int) -> dict[str, Any]:
        response = self._request("GET", f"/api/v1/rds/common/declarations/{declaration_id}")
        return response.json()

    def check(self, number: str) -> dict[str, Any]:
        decl = self.find_by_number(number)
        if not decl:
            return {"exists": False, "number": number}

        card = self.get_card(decl["id"])

        return {
            "exists": True,
            "id": decl["id"],
            "number": card["number"],
            "applicant": card["applicant"]["fullName"],
            "manufacturer": card["manufacturer"]["fullName"],
            "product": card["product"]["fullName"],
            "reg_date": card["declRegDate"],
            "end_date": card["declEndDate"],
        }


class FsaCertificateClient(BaseFsaClient):
    def find_by_number(self, number: str) -> dict[str, Any] | None:
        payload = {
            "size": 10,
            "page": 0,
            "filter": {
                "idCertScheme": [],
                "regDate": {"startDate": None, "endDate": None},
                "endDate": {"startDate": None, "endDate": None},
                "columnsSearch": [{"name": "number", "search": number, "type": 0}],
            },
            "columnsSort": [{"column": "date", "sort": "DESC"}],
        }

        response = self._request("POST", "/api/v1/rss/common/certificates/get", json=payload)
        items = response.json().get("items", [])
        return items[0] if items else None

    def get_card(self, certificate_id: int) -> dict[str, Any]:
        response = self._request("GET", f"/api/v1/rss/common/certificates/{certificate_id}")
        return response.json()

    def check(self, number: str) -> dict[str, Any]:
        cert = self.find_by_number(number)
        if not cert:
            return {"exists": False, "number": number}

        card = self.get_card(cert["id"])

        return {
            "exists": True,
            "id": cert["id"],
            "number": card["number"],
            "applicant": card["applicant"]["fullName"],
            "manufacturer": card["manufacturer"]["fullName"],
            "product": card["product"]["fullName"],
            "reg_date": card["certRegDate"],
            "end_date": card["certEndDate"],
        }


_shared_rate_limiter: RedisRateLimiter | None = None
_shared_circuit_breaker: RedisCircuitBreaker | None = None
_shared_token_store: FsaTokenStore | None = None
_declaration_client: FsaDeclarationClient | None = None
_certificate_client: FsaCertificateClient | None = None


def _get_shared_rate_limiter() -> RedisRateLimiter:
    global _shared_rate_limiter
    if _shared_rate_limiter is None:
        _shared_rate_limiter = RedisRateLimiter(
            redis_client=get_redis_client(),
            key=REDIS_KEY_RATE_LIMIT,
            rps=settings.FSA_RATE_LIMIT_RPS,
            max_wait_seconds=settings.FSA_RATE_LIMIT_MAX_WAIT_SEC,
        )
    return _shared_rate_limiter


def _get_shared_circuit_breaker() -> RedisCircuitBreaker:
    global _shared_circuit_breaker
    if _shared_circuit_breaker is None:
        _shared_circuit_breaker = RedisCircuitBreaker(
            redis_client=get_redis_client(),
            state_key=REDIS_KEY_CIRCUIT,
            failure_threshold=settings.FSA_CB_FAILURE_THRESHOLD,
            open_seconds=settings.FSA_CB_OPEN_SECONDS,
            max_open_seconds=settings.FSA_CB_MAX_OPEN_SECONDS,
            trial_ttl_seconds=settings.FSA_TIMEOUT + 5,
        )
    return _shared_circuit_breaker


def _get_shared_token_store() -> FsaTokenStore:
    global _shared_token_store
    if _shared_token_store is None:
        _shared_token_store = FsaTokenStore(
            redis_client=get_redis_client(),
            key=REDIS_KEY_TOKEN,
            lock_key=REDIS_KEY_TOKEN_LOCK,
            default_ttl_seconds=settings.FSA_TOKEN_CACHE_TTL,
        )
    return _shared_token_store


def get_fsa_circuit_breaker() -> RedisCircuitBreaker:
    return _get_shared_circuit_breaker()


def get_fsa_declaration_client() -> FsaDeclarationClient:
    global _declaration_client
    if _declaration_client is None:
        _declaration_client = FsaDeclarationClient(
            rate_limiter=_get_shared_rate_limiter(),
            circuit_breaker=_get_shared_circuit_breaker(),
            token_store=_get_shared_token_store(),
        )
    return _declaration_client


def get_fsa_certificate_client() -> FsaCertificateClient:
    global _certificate_client
    if _certificate_client is None:
        _certificate_client = FsaCertificateClient(
            rate_limiter=_get_shared_rate_limiter(),
            circuit_breaker=_get_shared_circuit_breaker(),
            token_store=_get_shared_token_store(),
        )
    return _certificate_client
