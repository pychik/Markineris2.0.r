from __future__ import annotations

from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import settings

from .constants import (
    API_PATH_DICTIONARIES_STATE,
    API_PATH_EXPORT_COLORS,
    API_PATH_EXPORT_COUNTRIES,
    API_PATH_EXPORT_TNVED_TEMPLATE,
)
from .exceptions import TezaurusApiError, TezaurusConfigurationError


def _flag_from_value(value: object, *, default: bool) -> bool:
    if isinstance(value, bool):
        return value

    if value is None:
        return default

    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


class TezaurusApiClient:
    """HTTP client for Tezaurus dictionaries API."""

    _RETRY_STATUSES = (429, 500, 502, 503, 504)

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_token: str | None = None,
        timeout: float | None = None,
        verify_ssl: bool | str | None = None,
        ca_cert: str | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = (base_url or settings.TEZAURUS_BASE_URL or "").strip().rstrip("/")
        self.api_token = (api_token if api_token is not None else settings.TEZAURUS_API_TOKEN or "").strip()
        self.timeout = float(timeout if timeout is not None else settings.TEZAURUS_TIMEOUT)

        ca_bundle = (ca_cert if ca_cert is not None else settings.TEZAURUS_CA_CERT or "").strip()
        verify_flag = verify_ssl if verify_ssl is not None else settings.TEZAURUS_VERIFY_SSL

        if ca_bundle:
            self.verify: bool | str = ca_bundle
        else:
            self.verify = _flag_from_value(verify_flag, default=True)

        if not self.base_url:
            raise TezaurusConfigurationError("TEZAURUS_BASE_URL is not configured")
        if not self.api_token:
            raise TezaurusConfigurationError("TEZAURUS_API_TOKEN is not configured")

        self.session = session or self._build_session()

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=3,
            connect=3,
            read=3,
            status=3,
            backoff_factor=1,
            status_forcelist=self._RETRY_STATUSES,
            allowed_methods=frozenset(["GET"]),
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _build_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Accept": "application/json",
        }

    def _request_json(self, path: str) -> dict[str, Any]:
        url = f"{self.base_url}{path}"

        try:
            response = self.session.get(
                url,
                headers=self._build_headers(),
                timeout=self.timeout,
                verify=self.verify,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise TezaurusApiError(f"Tezaurus request failed for {path}: {exc}") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise TezaurusApiError(f"Tezaurus response is not valid JSON for {path}") from exc

        if not isinstance(payload, dict):
            raise TezaurusApiError(f"Tezaurus response has unexpected payload type for {path}")

        return payload

    @staticmethod
    def _error_text(payload: dict[str, Any]) -> str:
        """Две ручки Тезауруса кладут текст ошибки в разные поля - читаем оба."""
        return payload.get("error") or payload.get("message") or "неизвестная ошибка"

    def _post_json(self, path: str, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        """POST без автоматических ретраев.

        Retry в сессии разрешён только для GET, и это принципиально:
        /processing-companies/select меняет состояние, каждый повтор сдвигает
        очередь раздачи компаний. Поэтому обе новые ручки вызываются через POST.

        Возвращает (HTTP-код, тело). Коды 4xx не считаются исключением: в них
        лежит осмысленный ответ - 409 «нет подходящей компании», 413 «слишком
        много позиций» и так далее. Решает вызывающий код.
        """
        url = f"{self.base_url}{path}"
        try:
            response = self.session.post(
                url,
                headers={**self._build_headers(), "Content-Type": "application/json"},
                json=body,
                timeout=self.timeout,
                verify=self.verify,
            )
        except requests.RequestException as exc:
            raise TezaurusApiError(f"Tezaurus request failed for {path}: {exc}") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            # 502/504 от прокси приходят HTML-страницей, а не JSON
            raise TezaurusApiError(
                f"Tezaurus response is not valid JSON for {path} (HTTP {response.status_code})"
            ) from exc

        if not isinstance(payload, dict):
            raise TezaurusApiError(f"Tezaurus response has unexpected payload type for {path}")

        if response.status_code >= 500:
            raise TezaurusApiError(
                f"Tezaurus {path} failed with HTTP {response.status_code}: {self._error_text(payload)}"
            )

        return response.status_code, payload

    def match_rd(self, order_id: int, positions: list[dict], category: str | None = None) -> dict[str, Any]:
        """Подобрать РД на все позиции заказа одним запросом.

        Ручка ничего не меняет на стороне Тезауруса - повторять безопасно.
        """
        body: dict[str, Any] = {"order_id": order_id, "positions": positions}
        if category:
            body["category"] = category

        status_code, payload = self._post_json("/api/v1/rd/match", body)
        if status_code >= 400:
            raise TezaurusApiError(
                f"Tezaurus rd/match rejected request (HTTP {status_code}, "
                f"code={payload.get('code')}): {self._error_text(payload)}"
            )
        return payload

    def select_processing_company(self, category: str, origin: str) -> dict[str, Any] | None:
        """Взять следующую компанию-обработчика под категорию и происхождение.

        ВНИМАНИЕ: меняет состояние. Каждый вызов сдвигает очередь раздачи,
        поэтому вызывать строго один раз на заказ и никогда - в цикле повторов
        или «чтобы посмотреть». Для просмотра есть export_processing_companies().

        Возвращает данные компании либо None, если под эту пару компания
        не настроена (HTTP 409) - повторять в этом случае бесполезно.
        """
        status_code, payload = self._post_json(
            "/api/v1/processing-companies/select",
            {"category": category, "origin": origin},
        )

        if status_code == 409 or payload.get("matched") is False:
            return None
        if status_code >= 400:
            raise TezaurusApiError(
                f"Tezaurus processing-companies/select rejected request "
                f"(HTTP {status_code}): {self._error_text(payload)}"
            )

        company = payload.get("company")
        if not isinstance(company, dict) or not company.get("title"):
            raise TezaurusApiError("Tezaurus processing-companies/select returned no company")
        return company

    def export_processing_companies(self) -> dict[str, Any]:
        """Полный список компаний. Состояние не меняет, вызывать можно свободно."""
        return self._request_json("/api/v1/export/processing-companies")

    def get_dictionaries_state(self) -> dict[str, Any]:
        return self._request_json(API_PATH_DICTIONARIES_STATE)

    def export_colors(self) -> dict[str, Any]:
        return self._request_json(API_PATH_EXPORT_COLORS)

    def export_countries(self) -> dict[str, Any]:
        return self._request_json(API_PATH_EXPORT_COUNTRIES)

    def export_tnved(self, category_slug: str) -> dict[str, Any]:
        path = API_PATH_EXPORT_TNVED_TEMPLATE.format(category_slug=category_slug)
        return self._request_json(path)

    def export_tnved_clothes(self) -> dict[str, Any]:
        return self.export_tnved("clothes")
