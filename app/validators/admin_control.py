from pydantic import BaseModel, Field


class BonusCodeSchema(BaseModel):
    code: str
    value: int


class UpdateBalanceSchema(BaseModel):
    amount: int = Field(alias="balanceAmount")
    operation_type: bool = Field(alias="balanceOperationType")
    comment: str = Field(alias="editBalanceComment")
    is_promo_correction: bool = Field(default=False, alias="isPromoCorrection")
