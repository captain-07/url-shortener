from datetime import datetime
from urllib.parse import urlsplit

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.clock import utcnow
from app.codegen import generate_code
from app.config import settings
from app.constants import RESERVED_ALIASES
from app.exceptions import (
    AliasTakenError,
    CodeGenerationError,
    LinkExpiredError,
    LinkNotFoundError,
    ReservedAliasError,
    SelfReferentialUrlError,
)
from app.models import Link

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


def _points_at_this_service(url: str) -> bool:
    """True if `url` has the same scheme and host as the shortener itself."""
    target = urlsplit(url)
    base = urlsplit(settings.base_url)
    return target.scheme == base.scheme and target.netloc.lower() == base.netloc.lower()


def create_link(
    db: Session,
    original_url: str,
    custom_alias: str | None,
    expires_at: datetime | None,
) -> Link:
    # Business rules live here rather than only in the Pydantic schema, so any
    # caller (CLI, background job, future endpoint) gets the same guarantees.
    if custom_alias and custom_alias.lower() in RESERVED_ALIASES:
        raise ReservedAliasError(custom_alias)
    if _points_at_this_service(original_url):
        raise SelfReferentialUrlError(original_url)

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


def record_click(db: Session, link: Link) -> None:
    """Atomically bump the counter. The increment happens inside the database,
    so concurrent redirects can't overwrite each other's updates.

    `synchronize_session=False` keeps SQLAlchemy from half-updating the loaded
    `link` object (it cannot evaluate `utcnow()` client-side). Callers must
    re-read the row if they need the new counters.
    """
    db.execute(
        update(Link)
        .where(Link.id == link.id)
        .values(click_count=Link.click_count + 1, last_clicked_at=utcnow())
        .execution_options(synchronize_session=False)
    )
    db.commit()
