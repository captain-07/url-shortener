from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import services
from app.config import settings
from app.database import get_db
from app.models import Link, as_utc
from app.schemas import LinkCreate, LinkResponse, StatsResponse

router = APIRouter(prefix="/links", tags=["links"])


def _to_response(link: Link) -> LinkResponse:
    return LinkResponse(
        code=link.code,
        short_url=f"{settings.base_url.rstrip('/')}/{link.code}",
        original_url=link.original_url,
        created_at=as_utc(link.created_at),
        expires_at=as_utc(link.expires_at),
    )


@router.post("", response_model=LinkResponse, status_code=201)
def create_link(payload: LinkCreate, db: Session = Depends(get_db)):
    link = services.create_link(
        db,
        original_url=str(payload.url),
        custom_alias=payload.custom_alias,
        expires_at=payload.expires_at,
    )
    return _to_response(link)


@router.get("/{code}/stats", response_model=StatsResponse)
def link_stats(code: str, db: Session = Depends(get_db)):
    link = services.get_link(db, code)  # 404 if unknown; no expiry check on purpose
    return StatsResponse(
        code=link.code,
        original_url=link.original_url,
        total_clicks=link.click_count,
        last_clicked_at=as_utc(link.last_clicked_at),
        created_at=as_utc(link.created_at),
        expires_at=as_utc(link.expires_at),
    )