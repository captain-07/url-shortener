from collections.abc import Mapping, Sequence
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import models  # noqa: F401  (registers tables on Base before create_all)
from app.database import Base, engine, get_db
from app.exceptions import AppError
from app.routers import links, redirect

TAGS_METADATA = [
    {"name": "links", "description": "Create short links and read their statistics."},
    {"name": "redirect", "description": "Resolve a short code to its original URL."},
    {"name": "health", "description": "Liveness probe for deployments."},
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fine for this scope; a production deployment would use Alembic migrations.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="URL Shortener API",
    version="1.0.0",
    description=(
        "Shorten URLs with optional custom aliases and expiry, redirect visitors, "
        "and read per-link click statistics."
    ),
    openapi_tags=TAGS_METADATA,
    lifespan=lifespan,
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    """One handler for every domain error: the exception owns its status/message."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail()})


def _summarise(errors: Sequence[Mapping[str, Any]]) -> str:
    parts = []
    for error in errors:
        location = ".".join(str(part) for part in error["loc"] if part != "body")
        parts.append(f"{location or 'body'}: {error['msg']}")
    return "; ".join(parts) or "Invalid request."


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Keep 422 bodies in the same `{"detail": "<string>"}` shape as every
    other error, while still exposing the per-field list for clients that want
    to render it programmatically."""
    errors = exc.errors()
    return JSONResponse(
        status_code=422,
        content={"detail": _summarise(errors), "errors": jsonable_encoder(errors)},
    )


@app.get("/health", tags=["health"], summary="Health check")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    """Cheap readiness probe: verifies the app is up and the database answers."""
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


app.include_router(links.router)
app.include_router(redirect.router)  # MUST be last: /{code} is a catch-all
