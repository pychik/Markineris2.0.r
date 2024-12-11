from pydantic import BaseModel


class DetailMinIOResponseDTO(BaseModel):
    data: bytes
    size: int
