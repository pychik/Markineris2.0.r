from pydantic.fields import Field
from pydantic.main import BaseModel


class BaseSchema(BaseModel):
    phone: str = Field(..., alias="phone")


class UserSchema(BaseSchema):
    email: str
    login_name: str = Field(..., alias="name")
    role: str
    status: bool
    password: str
    created_at: str | None
    admin_parent_id: int | None = Field(default=None)
    client_code: str | None = Field(default="NO CODE")
    is_crm: bool = Field(default=False)


class PartnerCodeSchema(BaseSchema):
    name: str
    code: str
    required_phone: bool = True
    required_email: bool = True


SchemaType = BaseSchema | UserSchema | PartnerCodeSchema
