from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class IndicatorValue(Base):
    """
    Stores one calculated indicator value.

    Example:

    RELIANCE
    EMA
    Period = 20
    Date = 2025-07-10
    Value = 1532.44
    """

    __tablename__ = "indicator_values"

    __table_args__ = (

        UniqueConstraint(
            "instrument_id",
            "trade_date",
            "indicator",
            "period",
            name="uq_indicator_value",
        ),

        Index(
            "ix_indicator_lookup",
            "instrument_id",
            "trade_date",
            "indicator",
            "period",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    instrument_id: Mapped[int] = mapped_column(
        ForeignKey("instruments.id"),
        nullable=False,
    )

    trade_date: Mapped[Date] = mapped_column(
        Date,
        nullable=False,
    )

    indicator: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    period: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    value: Mapped[Decimal] = mapped_column(
        Numeric(18, 6),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    instrument = relationship(
        "Instrument",
    )