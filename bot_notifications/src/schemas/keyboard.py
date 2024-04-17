from pydantic import BaseModel


class ButtonSchema(BaseModel):
    text: str
    data: str


class ButtonListSchema(BaseModel):
    buttons: list[ButtonSchema]
