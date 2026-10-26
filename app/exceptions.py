"""Domain errors.

Each error knows the HTTP status and message it maps to, so the transport layer
can translate all of them with a single exception handler (see `app/main.py`).
Services raise these without importing FastAPI.
"""

from datetime import datetime


class AppError(Exception):
    """Base class for errors that are safe to show to API clients."""

    status_code = 500

    def detail(self) -> str:
        return "Internal server error."


class LinkNotFoundError(AppError):
    status_code = 404

    def __init__(self, code: str):
        self.code = code

    def detail(self) -> str:
        return f"Short link '{self.code}' does not exist."


class LinkExpiredError(AppError):
    status_code = 410

    def __init__(self, code: str, expired_at: datetime):
        self.code = code
        self.expired_at = expired_at

    def detail(self) -> str:
        stamp = self.expired_at
        suffix = "Z" if stamp.tzinfo is None else ""  # stored values are naive UTC
        return (
            f"Short link '{self.code}' expired on {stamp.isoformat()}{suffix} "
            "and is no longer available."
        )


class AliasTakenError(AppError):
    status_code = 409

    def __init__(self, alias: str):
        self.alias = alias

    def detail(self) -> str:
        return f"Alias '{self.alias}' is already taken. Please choose a different alias."


class ReservedAliasError(AppError):
    status_code = 422

    def __init__(self, alias: str):
        self.alias = alias

    def detail(self) -> str:
        return f"'{self.alias}' is a reserved word and cannot be used as an alias."


class SelfReferentialUrlError(AppError):
    status_code = 422

    def __init__(self, url: str):
        self.url = url

    def detail(self) -> str:
        return "URL points back at this service, which would create a redirect loop."


class CodeGenerationError(AppError):
    """Could not find a free short code after several attempts."""

    status_code = 500

    def detail(self) -> str:
        return "Could not generate a unique short code. Please retry."
