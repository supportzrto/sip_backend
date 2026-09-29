from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    Boolean,
    BigInteger,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class FeatureValue(Base):
    """
    Stores one feature value for one
    instrument on one trading day.
    """

    __tablename__ = "feature_values"

    __table_args__ = (

        UniqueConstraint(
            "instrument_id",
            "feature_definition_id",
            "trade_date",
            name="uq_feature_value",
        ),

        Index(
            "ix_feature_instrument_date",
            "instrument_id",
            "trade_date",
        ),

        Index(
            "ix_feature_definition_date",
            "feature_definition_id",
            "trade_date",
        ),

        Index(
            "ix_feature_lookup",
            "instrument_id",
            "feature_definition_id",
        ),

    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    instrument_id: Mapped[int] = mapped_column(
        ForeignKey("instruments.id"),
        nullable=False,
    )

    feature_definition_id: Mapped[int] = mapped_column(
        ForeignKey("feature_definitions.id"),
        nullable=False,
    )

    trade_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    decimal_value: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 8),
        nullable=True,
    )

    integer_value: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    boolean_value: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    instrument = relationship(
        "Instrument",
        back_populates="historical_feature_values",
    )

    feature_definition = relationship(
        "FeatureDefinition",
        back_populates="historical_feature_values",
    )