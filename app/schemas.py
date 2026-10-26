from datetime import UTC, datetime
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from app.clock import as_utc, utcnow
from app.config import settings
from app.constants import MAX_ALIAS_LENGTH, MAX_URL_LENGTH, MIN_ALIAS_LENGTH

_ALIAS_PATTERN = rf"^[A-Za-z0-9_-]{{{MIN_ALIAS_LENGTH},{MAX_ALIAS_LENGTH}}}$"


class LinkCreate(BaseModel):
    """Payload for POST /links."""

    # Reject unknown keys: a typo like "custom_alais" must fail loudly instead
    # of silently creating a link with a generated code.
    model_config = ConfigDict(extra="forbid")

    url: HttpUrl = Field(
        description="Long URL to shorten. Only http and https are accepted.",
        examples=["https://example.com/some/long/path"],
    )
    custom_alias: str | None = Field(
        default=None,
        pattern=_ALIAS_PATTERN,
        description=(
            f"{MIN_ALIAS_LENGTH}-{MAX_ALIAS_LENGTH} chars: letters, digits, '-' or '_'. "
            "Aliases are case-sensitive."
        ),
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

    @field_validator("expires_at")
    @classmethod
    def expiry_in_future(cls, v: datetime | None) -> datetime | None:
        if v is None:
            return v
        if v.tzinfo is not None:  # normalise to naive UTC, matching the DB convention
            v = v.astimezone(UTC).replace(tzinfo=None)
        if v <= utcnow():
            raise ValueError("expires_at must be in the future.")
        return v


class _LinkRecord(Protocol):
    """The subset of the ORM `Link` row that the API serialises."""

    code: str
    original_url: str
    created_at: datetime
    expires_at: datetime | None
    click_count: int
    last_clicked_at: datetime | None


class _UTCTimestamps(BaseModel):
    """Emit every stored timestamp with an explicit UTC offset."""

    @field_validator(
        "created_at", "expires_at", "last_clicked_at", mode="after", check_fields=False
    )
    @classmethod
    def _stored_datetimes_are_utc(cls, v: datetime | None) -> datetime | None:
        return as_utc(v)


class LinkBase(_UTCTimestamps):
    code: str
    original_url: str
    created_at: datetime
    expires_at: datetime | None


class LinkResponse(LinkBase):
    short_url: str

    @classmethod
    def from_link(cls, link: _LinkRecord) -> "LinkResponse":
        return cls(
            code=link.code,
            original_url=link.original_url,
            short_url=f"{settings.base_url.rstrip('/')}/{link.code}",
            created_at=link.created_at,
            expires_at=link.expires_at,
        )


class StatsResponse(LinkBase):
    total_clicks: int
    last_clicked_at: datetime | None

    @classmethod
    def from_link(cls, link: _LinkRecord) -> "StatsResponse":
        return cls(
            code=link.code,
            original_url=link.original_url,
            total_clicks=link.click_count,
            last_clicked_at=link.last_clicked_at,
            created_at=link.created_at,
            expires_at=link.expires_at,
        )


class ErrorResponse(BaseModel):
    """Shape of every error body, documented in the OpenAPI schema."""

    detail: str
