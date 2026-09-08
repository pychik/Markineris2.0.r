from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from config import settings

from .api_client import TezaurusApiClient
from .constants import API_PATH_PROCESSING_COMPANIES_SELECT, API_PATH_PROCESSING_COMPANIES_SELECT_BATCH


PROCESSING_COMPANIES_BATCH_LIMIT = 200


PROCESSING_COMPANY_CATEGORIES = frozenset(
    (
        "clothes",
        "shoes",
        "parfum",
        "cosmetics",
        "toys",
        "home_goods",
    )
)
PROCESSING_COMPANY_ORIGINS = frozenset(("rf", "import"))

CATEGORY_TO_PROCESSING_COMPANY_CATEGORY = {
    "clothes": "clothes",
    "одежда": "clothes",
    "common": "clothes",
    "underwear": "clothes",
    "белье": "clothes",
    "linen": "clothes",
    "socks": "clothes",
    "носки": "clothes",
    "носки и прочее": "clothes",
    "swimming_accessories": "clothes",
    "купальные принадлежности": "clothes",
    "hats": "clothes",
    "шляпы": "clothes",
    "gloves": "clothes",
    "перчатки": "clothes",
    "shawls": "clothes",
    "шали": "clothes",
    "shoes": "shoes",
    "обувь": "shoes",
    "parfum": "parfum",
    "парфюм": "parfum",
    "духи": "parfum",
    "cosmetics": "cosmetics",
    "косметика": "cosmetics",
    "toys": "toys",
    "игрушки": "toys",
    "home_goods": "home_goods",
    "house_goods": "home_goods",
    "товары для дома": "home_goods",
}

RF_COUNTRY_VALUES = frozenset(
    (
        "rf",
        "ru",
        "rus",
        "643",
        "рф",
        "россия",
        "российская федерация",
        settings.COUNTRY_RUSSIA.lower(),
    )
)


@dataclass(frozen=True)
class ProcessingCompaniesRequest:
    category: str
    origin: str

    def as_payload(self) -> dict[str, str]:
        return {
            "category": self.category,
            "origin": self.origin,
        }

    def as_batch_payload(self, client_id: str) -> dict[str, str]:
        return {
            "client_id": client_id,
            **self.as_payload(),
        }


class ProcessingCompaniesClient:
    def __init__(self, *, api_client: TezaurusApiClient | None = None) -> None:
        self.api_client = api_client or TezaurusApiClient()

    @staticmethod
    def normalize_category(category: str) -> str:
        value = (category or "").strip().lower()
        normalized = CATEGORY_TO_PROCESSING_COMPANY_CATEGORY.get(value)

        if normalized not in PROCESSING_COMPANY_CATEGORIES:
            allowed = ", ".join(sorted(PROCESSING_COMPANY_CATEGORIES))
            raise ValueError(f"Unsupported processing company category: {category!r}. Allowed: {allowed}")

        return normalized

    @staticmethod
    def normalize_origin(origin: str) -> str:
        value = (origin or "").strip().lower()
        if value not in PROCESSING_COMPANY_ORIGINS:
            allowed = ", ".join(sorted(PROCESSING_COMPANY_ORIGINS))
            raise ValueError(f"Unsupported processing company origin: {origin!r}. Allowed: {allowed}")

        return value

    @staticmethod
    def origin_from_country(country: str) -> str:
        value = (country or "").strip().lower()
        if not value:
            raise ValueError("Country is required to detect processing company origin")

        return "rf" if value in RF_COUNTRY_VALUES else "import"

    def build_request(
        self,
        *,
        category: str,
        origin: str | None = None,
        country: str | None = None,
    ) -> ProcessingCompaniesRequest:
        if origin:
            normalized_origin = self.normalize_origin(origin)
        elif country:
            normalized_origin = self.origin_from_country(country)
        else:
            raise ValueError("Either origin or country must be provided")

        return ProcessingCompaniesRequest(
            category=self.normalize_category(category),
            origin=normalized_origin,
        )

    def select(self, *, category: str, origin: str) -> dict[str, Any]:
        request_payload = self.build_request(category=category, origin=origin).as_payload()
        return self.api_client.post_json(API_PATH_PROCESSING_COMPANIES_SELECT, request_payload)

    def select_by_country(self, *, category: str, country: str) -> dict[str, Any]:
        request_payload = self.build_request(category=category, country=country).as_payload()
        return self.api_client.post_json(API_PATH_PROCESSING_COMPANIES_SELECT, request_payload)

    def select_batch(self, items: list[dict[str, str]]) -> dict[str, Any]:
        if not items:
            raise ValueError("Processing companies batch items are required")
        if len(items) > PROCESSING_COMPANIES_BATCH_LIMIT:
            raise ValueError(f"Processing companies batch limit is {PROCESSING_COMPANIES_BATCH_LIMIT}")

        request_items: list[dict[str, str]] = []
        for item in items:
            client_id = (item.get("client_id") or "").strip()
            if not client_id:
                raise ValueError("Processing companies batch item client_id is required")

            processing_request = self.build_request(
                category=item.get("category", ""),
                origin=item.get("origin", ""),
            )
            request_items.append(processing_request.as_batch_payload(client_id))

        return self.api_client.post_json(
            API_PATH_PROCESSING_COMPANIES_SELECT_BATCH,
            {"items": request_items},
        )


def build_default_processing_companies_client() -> ProcessingCompaniesClient:
    return ProcessingCompaniesClient()
