from pydantic import BaseModel, Field


class BonusCodeSchema(BaseModel):
    code: str
    value: int


class UpdateBalanceSchema(BaseModel):
    amount: int = Field(alias="balanceAmount")
    operation_type: bool = Field(alias="balanceOperationType")
