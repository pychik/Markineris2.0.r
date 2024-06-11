from pydantic import BaseModel


class BaseModelWithStatusCode(BaseModel):
    status_code: int


class NotOkResponseSchema(BaseModelWithStatusCode):
    detail: str
