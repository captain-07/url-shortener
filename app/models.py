from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utcnow() -> datetime:
    """Naive UTC. SQLite drops tzinfo, so we store UTC consistently
    and treat every stored datetime as UTC."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Link(Base):
    __tablename__ = "links"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)  # UNIQUE = also indexed
    original_url: Mapped[str] = mapped_column(String(2048))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    click_count: Mapped[int] = mapped_column(default=0)
    last_clicked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)