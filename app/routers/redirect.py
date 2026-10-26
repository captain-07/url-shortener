from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app import services
from app.database import get_db
from app.schemas import ErrorResponse

router = APIRouter(tags=["redirect"])


@router.get(
    "/{code}",
    status_code=302,
    summary="Redirect to the original URL",
    responses={
        404: {"model": ErrorResponse, "description": "No link with that code."},
        410: {"model": ErrorResponse, "description": "The link has expired."},
    },
)
def redirect_to_original(code: str, db: Session = Depends(get_db)):
    link = services.get_link(db, code)  # 404 if unknown
    services.ensure_active(link)  # 410 if expired
    services.record_click(db, link)  # only reached for valid, active links
    return RedirectResponse(
        url=link.original_url,
        status_code=302,
        # 302 is only useful if proxies don't cache it: a cached redirect would
        # skip both click counting and expiry checks.
        headers={"Cache-Control": "no-store"},
    )
