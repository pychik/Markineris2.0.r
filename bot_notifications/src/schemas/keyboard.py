from pydantic import BaseModel


class InlineButtonSchema(BaseModel):
    text: str
    data: str


class ReplyButtonSchema(BaseModel):
    text: str


class ButtonListSchema(BaseModel):
    buttons: list[InlineButtonSchema | ReplyButtonSchema]
