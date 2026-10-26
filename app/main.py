from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app import models  # noqa: F401  (registers tables on Base before create_all)
from app.database import Base, engine
from app.exceptions import (
    AliasTakenError,
    CodeGenerationError,
    LinkExpiredError,
    LinkNotFoundError,
)
from app.routers import links, redirect


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)  # fine for this scope; use Alembic migrations in production
    yield


app = FastAPI(title="URL Shortener API", version="1.0.0", lifespan=lifespan)


@app.exception_handler(LinkNotFoundError)
async def not_found_handler(request: Request, exc: LinkNotFoundError):
    return JSONResponse(status_code=404, content={"detail": f"Short link '{exc.code}' does not exist."})


@app.exception_handler(LinkExpiredError)
async def expired_handler(request: Request, exc: LinkExpiredError):
    return JSONResponse(
        status_code=410,
        content={"detail": f"Short link '{exc.code}' expired on {exc.expired_at.isoformat()}Z and is no longer available."},
    )


@app.exception_handler(AliasTakenError)
async def alias_taken_handler(request: Request, exc: AliasTakenError):
    return JSONResponse(
        status_code=409,
        content={"detail": f"Alias '{exc.alias}' is already taken. Please choose a different alias."},
    )


@app.exception_handler(CodeGenerationError)
async def codegen_handler(request: Request, exc: CodeGenerationError):
    return JSONResponse(status_code=500, content={"detail": "Could not generate a unique short code. Please retry."})


app.include_router(links.router)
app.include_router(redirect.router)  # MUST be last: /{code} is a catch-all