from datetime import datetime, UTC
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    # Only imported for type checkers (Pylance/mypy) -- never
    # actually executed at runtime, so this doesn't reintroduce the
    # watchlist.py <-> watchlist_item.py circular import. Runtime
    # relationship resolution still happens via the quoted string
    # names below, resolved lazily against SQLAlchemy's model
    # registry once every model is loaded.
    from app.models.instrument import Instrument
    from app.models.watchlist import Watchlist


class WatchlistItem(Base):
    """
    One symbol's membership in a watchlist.
    """

    __tablename__ = "watchlist_items"

    __table_args__ = (
        UniqueConstraint(
            "watchlist_id",
            "instrument_id",
            name="uq_watchlist_item",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    watchlist_id: Mapped[int] = mapped_column(
        ForeignKey("watchlists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    instrument_id: Mapped[int] = mapped_column(
        ForeignKey("instruments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    watchlist: Mapped["Watchlist"] = relationship(
        "Watchlist",
        back_populates="items",
    )

    instrument: Mapped["Instrument"] = relationship(
        "Instrument",
    )

    @property
    def symbol(self) -> str:
        """
        Convenience passthrough so API schemas (from_attributes) can
        read `item.symbol` directly instead of `item.instrument.symbol`.
        """
        return self.instrument.symbol