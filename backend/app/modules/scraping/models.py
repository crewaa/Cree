"""
Scrape job records.

Scrapes run as fire-and-forget FastAPI BackgroundTasks. Before this table
existed, a failure was invisible: the endpoint returned `{"status": "scraping"}`
unconditionally (even for a user that did not exist), the task logged an error
to stdout, and the frontend polled the analytics endpoint until it gave up. The
creator saw an empty dashboard with no explanation and no way to tell whether
the scrape had failed or was simply slow.

One row is written per scrape attempt, so both the user and we can see what
actually happened.
"""

from datetime import datetime

from sqlalchemy import String, ForeignKey, DateTime, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ScrapePlatform:
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"


class ScrapeStatus:
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"


class ScrapeJob(Base):
    __tablename__ = "scrape_jobs"

    __table_args__ = (
        # Supports "latest job for this user on this platform", the only read pattern.
        Index("ix_scrape_jobs_user_platform_started", "user_id", "platform", "started_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    platform: Mapped[str] = mapped_column(String)  # instagram | youtube
    status: Mapped[str] = mapped_column(String)    # running | success | error

    #: Human-readable outcome. For failures this is the reason the creator sees,
    #: so it must never contain internal detail such as tokens or stack traces.
    message: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship(back_populates="scrape_jobs")
