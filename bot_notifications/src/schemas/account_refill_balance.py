from enum import StrEnum

from pydantic import BaseModel

from src.schemas.base import BaseModelWithStatusCode


class RequisiteType(StrEnum):
    qr_code = "qr_code"
    requisite_number = "requisite_number"


class RequisiteIn(BaseModelWithStatusCode):
    requisite_id: int
    requisite: str
    requisite_type: RequisiteType = RequisiteType.qr_code


class PromoCodeIn(BaseModelWithStatusCode):
    amount: int
    promo_id: int


class TransactionCreateOut(BaseModel):
    amount: int
    status: int
    promo_info: str
    user_id: int
    sa_id: int
    bill_path: str
    promo_id: int | None = None


class TransactionCreateResultIn(BaseModelWithStatusCode):
    detail: str


ReturnModelFromMarkineris = RequisiteIn | PromoCodeIn
