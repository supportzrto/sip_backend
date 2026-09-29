from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
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


class FeatureSnapshot(Base):
    """
    Stores the latest value of every feature
    for every instrument.
    """

    __tablename__ = "feature_snapshot"

    __table_args__ = (

        UniqueConstraint(
            "instrument_id",
            "feature_definition_id",
            name="uq_feature_snapshot",
        ),

        Index(
            "ix_snapshot_instrument",
            "instrument_id",
        ),

        Index(
            "ix_snapshot_feature",
            "feature_definition_id",
        ),

        Index(
            "ix_snapshot_lookup",
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

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    instrument = relationship(
        "Instrument",
        back_populates="feature_snapshots",
    )

    feature_definition = relationship(
        "FeatureDefinition",
        back_populates="feature_snapshots",
    )