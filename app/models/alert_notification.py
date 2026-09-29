from __future__ import annotations

from datetime import datetime, UTC

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class AlertNotification(Base):
    """
    A record of one symbol newly matching one alert rule, and being
    emailed to the rule's owner. This is a history/audit log -- the
    live "have we already told them about this one" decision is made
    from AlertRule.last_matched_symbols, not by querying this table.
    """

    __tablename__ = "alert_notifications"

    id: Mapped[int] = mapped_column(primary_key=True)

    alert_rule_id: Mapped[int] = mapped_column(
        ForeignKey("alert_rules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    instrument_id: Mapped[int] = mapped_column(
        ForeignKey("instruments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Denormalized, same reasoning as ScanResult.symbol: keeps this
    # history readable/stable even if the instrument's symbol
    # changes later.
    symbol: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    reasons: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    notified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    alert_rule = relationship(
        "AlertRule",
        back_populates="notifications",
    )

    instrument = relationship(
        "Instrument",
    )