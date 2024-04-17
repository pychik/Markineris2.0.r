from pydantic import BaseModel


class NotificationMessage(BaseModel):
    chat_id: int
    message: str
