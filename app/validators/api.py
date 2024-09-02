from pydantic import BaseModel, field_validator


class TransactionInData(BaseModel):
    amount: int
    status: int
    promo_info: str
    user_id: int
    sa_id: int
    bill_path: str
    promo_id: int | None = None
    is_bonus: bool = False

    @field_validator('promo_id',  mode='before')
    @classmethod
    def promo_id_receive_none(cls, v: str) -> int | None:
        # todo: request.form засовывает NoneType объект в строку и поэтому тут такой костыль
        if v in ["None", "null", ""]:
            return None
        return int(v)


class TransactionCheckStatusInData(BaseModel):
    user_id: int
    sa_id: int
    bill_path: str


class PromoBonusCheckInData(BaseModel):
    user_id: int
    code: str
    is_bonus: bool = False

    @field_validator('user_id',  mode='before')
    @classmethod
    def user_id_receive_none(cls, v: str) -> int | None:
        # todo: request.form засовывает NoneType объект в строку и поэтому тут такой костыль
        if v in ["None", "null", ""]:
            return None
        return int(v)
