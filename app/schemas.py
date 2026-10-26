from datetime import datetime, timezone

from pydantic import BaseModel, Field, HttpUrl, field_validator

from app.models import utcnow

RESERVED_ALIASES = {"links", "docs", "redoc"}
MAX_URL_LENGTH = 2048  # must match the DB column size


class LinkCreate(BaseModel):
    url: HttpUrl
    custom_alias: str | None = Field(
        default=None,
        pattern=r"^[A-Za-z0-9_-]{3,32}$",
        description="3-32 chars: letters, digits, '-' or '_'.",
        examples=["my-link"],
    )
    expires_at: datetime | None = Field(
        default=None,
        description="ISO 8601, must be in the future. Naive values are treated as UTC.",
        examples=["2026-12-31T23:59:59Z"],
    )

    @field_validator("url")
    @classmethod
    def url_not_too_long(cls, v: HttpUrl) -> HttpUrl:
        if len(str(v)) > MAX_URL_LENGTH:
            raise ValueError(f"URL must be at most {MAX_URL_LENGTH} characters.")
        return v

    @field_validator("custom_alias")
    @classmethod
    def alias_not_reserved(cls, v: str | None) -> str | None:
        if v is not None and v.lower() in RESERVED_ALIASES:
            raise ValueError(f"'{v}' is a reserved word and cannot be used as an alias.")
        return v

    @field_validator("expires_at")
    @classmethod
    def expiry_in_future(cls, v: datetime | None) -> datetime | None:
        if v is None:
            return v
        if v.tzinfo is not None:  # normalise to naive UTC, matching the DB convention
            v = v.astimezone(timezone.utc).replace(tzinfo=None)
        if v <= utcnow():
            raise ValueError("expires_at must be in the future.")
        return v


class LinkResponse(BaseModel):
    code: str
    short_url: str
    original_url: str
    created_at: datetime
    expires_at: datetime | None