from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class DailyCandle(Base):
    __tablename__ = "daily_candles"

    __table_args__ = (
        UniqueConstraint(
            "instrument_id",
            "trade_date",
            name="uq_daily_candle_instrument_date",
        ),
        Index(
            "ix_daily_candle_instrument_date",
            "instrument_id",
            "trade_date",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    instrument_id: Mapped[int] = mapped_column(
        ForeignKey("instruments.id"),
        nullable=False,
    )

    trade_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    open: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
    )

    high: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
    )

    low: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
    )

    close: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
    )

    volume: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    instrument = relationship(
        "Instrument",
        back_populates="daily_candles",
    )