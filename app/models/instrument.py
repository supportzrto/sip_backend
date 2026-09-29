from datetime import datetime, UTC

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    String,
)
from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.daily_candle import DailyCandle

from app.database.base import Base

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.feature.value import FeatureValue

if TYPE_CHECKING:
    from app.models.feature.snapshot import FeatureSnapshot


class Instrument(Base):
    __tablename__ = "instruments"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    symbol: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )

    company_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    exchange: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    instrument_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    isin: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    provider: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    provider_token: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
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

    daily_candles: Mapped[list["DailyCandle"]] = relationship(
        "DailyCandle",
        back_populates="instrument",
        cascade="all, delete-orphan",
    )

    historical_feature_values: Mapped[list["FeatureValue"]] = relationship(
        "FeatureValue",
        back_populates="instrument",
        cascade="all, delete-orphan",
    )

    feature_snapshots: Mapped[list["FeatureSnapshot"]] = relationship(
        "FeatureSnapshot",
        back_populates="instrument",
        cascade="all, delete-orphan",
    )
