from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.clock import utcnow
from app.constants import CODE_COLUMN_LENGTH, MAX_URL_LENGTH
from app.database import Base


class Link(Base):
    """A shortened link plus its click counters."""

    __tablename__ = "links"

    id: Mapped[int] = mapped_column(primary_key=True)
    # UNIQUE creates the index that every redirect lookup relies on.
    code: Mapped[str] = mapped_column(String(CODE_COLUMN_LENGTH), unique=True)
    original_url: Mapped[str] = mapped_column(String(MAX_URL_LENGTH))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    click_count: Mapped[int] = mapped_column(default=0)
    last_clicked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
