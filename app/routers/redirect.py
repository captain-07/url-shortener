from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app import services
from app.database import get_db

router = APIRouter(tags=["redirect"])


@router.get("/{code}", status_code=302)
def redirect_to_original(code: str, db: Session = Depends(get_db)):
    link = services.get_link(db, code)   # 404 if unknown
    services.ensure_active(link)         # 410 if expired
    # Step 9 adds click recording here
    return RedirectResponse(url=link.original_url, status_code=302)