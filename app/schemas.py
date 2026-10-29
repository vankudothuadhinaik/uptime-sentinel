from datetime import datetime

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class AuthIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MonitorIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    url: AnyHttpUrl
    interval_seconds: int = Field(default=60, ge=30, le=86400)
    timeout_seconds: int = Field(default=10, ge=1, le=30)
    public: bool = False

    @field_validator("url")
    @classmethod
    def https_or_http(cls, value: AnyHttpUrl) -> AnyHttpUrl:
        if value.scheme not in {"http", "https"}:
            raise ValueError("only http and https URLs are supported")
        return value


class MonitorPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    url: AnyHttpUrl | None = None
    interval_seconds: int | None = Field(default=None, ge=30, le=86400)
    timeout_seconds: int | None = Field(default=None, ge=1, le=30)
    is_paused: bool | None = None
    public: bool | None = None

    @model_validator(mode="after")
    def reject_explicit_nulls(self):
        # Optional annotations let a client omit any field. Explicit nulls must
        # still be rejected for columns that are non-nullable in the database.
        non_nullable = (
            "name",
            "url",
            "interval_seconds",
            "timeout_seconds",
            "is_paused",
            "public",
        )
        for field_name in non_nullable:
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class MonitorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    url: str
    interval_seconds: int
    timeout_seconds: int
    is_paused: bool
    public: bool


class CheckOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    checked_at: datetime
    is_up: bool
    status_code: int | None
    latency_ms: int | None
    error_category: str | None


class IncidentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    started_at: datetime
    resolved_at: datetime | None
    failure_count: int
