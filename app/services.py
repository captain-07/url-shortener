from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.codegen import generate_code
from app.config import settings
from app.exceptions import (
    AliasTakenError,
    CodeGenerationError,
    LinkExpiredError,
    LinkNotFoundError,
)
from app.models import Link, utcnow

MAX_CODE_ATTEMPTS = 5


def _insert(db: Session, code: str, original_url: str, expires_at: datetime | None) -> Link:
    link = Link(code=code, original_url=original_url, expires_at=expires_at)
    db.add(link)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()  # session is unusable until rolled back
        raise
    return link


def create_link(
    db: Session,
    original_url: str,
    custom_alias: str | None,
    expires_at: datetime | None,
) -> Link:
    if custom_alias:
        try:
            return _insert(db, custom_alias, original_url, expires_at)
        except IntegrityError:
            raise AliasTakenError(custom_alias) from None

    for _ in range(MAX_CODE_ATTEMPTS):
        try:
            return _insert(db, generate_code(settings.code_length), original_url, expires_at)
        except IntegrityError:
            continue  # extremely rare collision: try a new code
    raise CodeGenerationError()


def get_link(db: Session, code: str) -> Link:
    link = db.scalar(select(Link).where(Link.code == code))
    if link is None:
        raise LinkNotFoundError(code)
    return link


def ensure_active(link: Link) -> None:
    if link.expires_at is not None and link.expires_at <= utcnow():
        raise LinkExpiredError(link.code, link.expires_at)