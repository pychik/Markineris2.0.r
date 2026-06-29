from pydantic import BaseModel, Field, field_validator


class ExternalProcessorCreateSchema(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    key_id: str | None = Field(default=None, min_length=3, max_length=128)
    shared_secret: str | None = Field(default=None, min_length=8, max_length=255)
    allowed_ips: list[str] | str
    minio_bucket_name: str = Field(min_length=1, max_length=255)
    minio_prefix: str = Field(min_length=1, max_length=255)
    ttl_seconds: int | None = Field(default=None, ge=1, le=86400)
    nonce_ttl_seconds: int | None = Field(default=None, ge=1, le=604800)
    batch_size: int | None = Field(default=None, ge=1, le=1000)
    confirmation_timeout_seconds: int | None = Field(default=None, ge=1, le=604800)
    source_label: str = Field(min_length=1, max_length=100)
    is_active: bool = True

    @field_validator('name', 'key_id', 'shared_secret', 'minio_bucket_name', 'source_label', mode='before')
    @classmethod
    def _strip_string(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @field_validator('minio_prefix', mode='before')
    @classmethod
    def _strip_prefix(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


class ExternalProcessorUpdateSchema(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    key_id: str | None = Field(default=None, min_length=3, max_length=128)
    shared_secret: str | None = Field(default=None, min_length=8, max_length=255)
    allowed_ips: list[str] | str | None = None
    minio_bucket_name: str | None = Field(default=None, min_length=1, max_length=255)
    minio_prefix: str | None = Field(default=None, max_length=255)
    ttl_seconds: int | None = Field(default=None, ge=1, le=86400)
    nonce_ttl_seconds: int | None = Field(default=None, ge=1, le=604800)
    batch_size: int | None = Field(default=None, ge=1, le=1000)
    confirmation_timeout_seconds: int | None = Field(default=None, ge=1, le=604800)
    source_label: str | None = Field(default=None, max_length=100)
    is_active: bool | None = None

    @field_validator('name', 'key_id', 'shared_secret', 'minio_bucket_name', 'source_label', mode='before')
    @classmethod
    def _strip_string(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @field_validator('minio_prefix', mode='before')
    @classmethod
    def _strip_prefix(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value