from datetime import datetime, UTC

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class AlertRule(Base):
    """
    "Notify me by email when <strategy> matches" -- optionally
    scoped to one of the user's watchlists rather than the whole
    instrument universe.

    Exactly one of strategy_key / saved_strategy_id is set:
    strategy_key names a built-in strategy (validated against
    app.scanner.strategies.AVAILABLE_STRATEGIES at the API layer --
    kept as a plain string column here rather than a DB enum so a
    new strategy key doesn't require a migration), while
    saved_strategy_id points at one of the user's own custom
    SavedStrategy expressions. Enforced by a DB CHECK constraint
    (see the migration) rather than only at the API layer, since a
    rule with both or neither would silently have no way to know
    what to scan for.
    """

    __tablename__ = "alert_rules"

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

    strategy_key: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # ON DELETE CASCADE: unlike a watchlist going away (which just
    # widens an alert back to the full universe -- see watchlist_id
    # below), a saved strategy going away leaves nothing for the
    # rule to scan for at all, so the rule genuinely can't continue
    # to mean anything and is removed with it.
    saved_strategy_id: Mapped[int | None] = mapped_column(
        ForeignKey("saved_strategies.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # NULL means "scan the whole instrument universe". Set, it
    # scopes matches down to just that watchlist's symbols. ON
    # DELETE SET NULL rather than CASCADE: deleting a watchlist
    # shouldn't silently delete alert rules built on top of it --
    # it should widen them back to the full universe instead, which
    # is a safe (if surprising) default the user can immediately see
    # and correct via the rule's watchlist_id being null.
    watchlist_id: Mapped[int | None] = mapped_column(
        ForeignKey("watchlists.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    last_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # The symbol set that matched on the *previous* run. Comparing
    # each new run's matches against this is what lets the alert
    # notify only on newly-triggered signals -- a symbol that keeps
    # matching day after day (e.g. RSI staying oversold) shouldn't
    # re-notify every single day, only the day it first starts
    # matching. Cleared back to matching the next run's result
    # regardless of whether anything "new" was found.
    last_matched_symbols: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    watchlist = relationship(
        "Watchlist",
    )

    saved_strategy = relationship(
        "SavedStrategy",
    )

    notifications = relationship(
        "AlertNotification",
        back_populates="alert_rule",
        cascade="all, delete-orphan",
        order_by="AlertNotification.notified_at.desc()",
    )

    __table_args__ = (
        CheckConstraint(
            "(strategy_key IS NOT NULL) != (saved_strategy_id IS NOT NULL)",
            name="ck_alert_rule_exactly_one_strategy_source",
        ),
    )