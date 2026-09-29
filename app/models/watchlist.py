from datetime import datetime, UTC
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    # Only imported for type checkers (Pylance/mypy) -- never
    # actually executed at runtime, so this doesn't reintroduce the
    # watchlist.py <-> watchlist_item.py circular import. Runtime
    # relationship resolution still happens via the quoted string
    # names below, resolved lazily against SQLAlchemy's model
    # registry once every model is loaded.
    from app.models.watchlist_item import WatchlistItem


class Watchlist(Base):
    """
    A named group of symbols a user cares about. Alert rules can
    optionally scope themselves to one watchlist (see AlertRule) so
    a user only gets notified about signals on stocks they've
    actually chosen to follow, instead of the entire universe.
    """

    __tablename__ = "watchlists"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "name",
            name="uq_watchlist_user_name",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    items: Mapped[list["WatchlistItem"]] = relationship(
        "WatchlistItem",
        back_populates="watchlist",
        cascade="all, delete-orphan",
    )