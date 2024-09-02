from pydantic import BaseModel


class BonusCodeSchema(BaseModel):
    code: str
    value: int
