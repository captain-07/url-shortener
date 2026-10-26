from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import services
from app.database import get_db
from app.schemas import ErrorResponse, LinkCreate, LinkResponse, StatsResponse

router = APIRouter(prefix="/links", tags=["links"])


@router.post(
    "",
    response_model=LinkResponse,
    status_code=201,
    summary="Create a short link",
    responses={
        409: {"model": ErrorResponse, "description": "The requested alias is already in use."},
        422: {"model": ErrorResponse, "description": "Invalid URL, alias or expiry."},
    },
)
def create_link(payload: LinkCreate, db: Session = Depends(get_db)) -> LinkResponse:
    link = services.create_link(
        db,
        original_url=str(payload.url),
        custom_alias=payload.custom_alias,
        expires_at=payload.expires_at,
    )
    return LinkResponse.from_link(link)


@router.get(
    "/{code}/stats",
    response_model=StatsResponse,
    summary="Click statistics for a short link",
    responses={
        404: {"model": ErrorResponse, "description": "No link with that code."},
    },
)
def link_stats(code: str, db: Session = Depends(get_db)) -> StatsResponse:
    link = services.get_link(db, code)  # 404 if unknown; no expiry check on purpose
    return StatsResponse.from_link(link)
