from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import services
from app.config import settings
from app.database import get_db
from app.models import Link, as_utc
from app.schemas import LinkCreate, LinkResponse

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