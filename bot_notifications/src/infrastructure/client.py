from typing import Any

from aiohttp import ClientSession, ClientError
from pydantic import ValidationError

from src.core.config import settings
from src.core.messages import UserMessages
from src.infrastructure.logger import logger
from src.schemas.account_refill_balance import (
    RequisiteIn,
    ReturnModelFromMarkineris,
    PromoCodeIn,
    TransactionCreateResultIn,
)
from src.schemas.base import NotOkResponseSchema


class BaseClient:
    ENDPOINTS = (
        CHECK_PROMO := settings.CHECK_PROMO,
        GET_REQS := settings.GET_REQS,
        CREATE_TRANSACTION := settings.CREATE_TRANSACTION,
    )

    INTERNAL_SERVER_ERROR_MESSAGE = UserMessages.INTERNAL_SERVER_ERROR

    def __init__(self):
        self._api_host = settings.API_HOST
        self.client = ClientSession(base_url=self._api_host)

    async def get_current_requisites(self):
        response = await self._make_request(
            url=self.GET_REQS,
            method="GET",
            headers={"MARKINERS_V2_TOKEN": settings.MARKINERS_V2_TOKEN},
        )

        return self._validate_response(response=response, schema=RequisiteIn)

    async def check_promo_code_for_existence(self, data: dict[str, Any]):
        response = await self._make_request(
            url=self.CHECK_PROMO,
            method="POST",
            headers={"MARKINERS_V2_TOKEN": settings.MARKINERS_V2_TOKEN},
            json=data,
        )

        return self._validate_response(response=response, schema=PromoCodeIn)

    async def create_transaction(self, data: dict[str, Any]):
        response = await self._make_request(
            url=self.CREATE_TRANSACTION,
            method="POST",
            headers={"MARKINERS_V2_TOKEN": settings.MARKINERS_V2_TOKEN},
            data=data
        )

        return self._validate_response(response=response, schema=TransactionCreateResultIn)

    async def _make_request(
            self,
            url: str,
            method: str,
            params: dict[str, Any] = None,
            headers: dict[str, Any] = None,
            **kwargs
    ) -> dict[str, Any] | NotOkResponseSchema:
        try:
            async with self.client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    **kwargs,
            ) as response:
                response_data = await response.json()
                if response.status in [200, 201]:
                    response_data.update({"status_code": response.status})
                    return response_data
                else:
                    return NotOkResponseSchema(status_code=response.status, detail=response_data.get('detail', 'Error'))
        except ClientError:
            logger.exception("Ошибка при запросе в марка-сервис")
            return NotOkResponseSchema(status_code=500, detail=self.INTERNAL_SERVER_ERROR_MESSAGE)

    @staticmethod
    def _validate_response(
            response: dict[str, Any] | NotOkResponseSchema,
            schema: ReturnModelFromMarkineris
    ) -> ReturnModelFromMarkineris | NotOkResponseSchema:
        if isinstance(response, NotOkResponseSchema):
            return response

        try:
            if isinstance(response, dict):
                return schema(**response)
        except ValidationError as e:
            logger.error(f'Validation error: {e}')
            return NotOkResponseSchema(status_code=500, detail=UserMessages.INTERNAL_SERVER_ERROR)

    async def close(self):
        await self.client.close()


def get_base_client() -> BaseClient:
    return BaseClient()
