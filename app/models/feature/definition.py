from datetime import datetime, UTC

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.feature.value import FeatureValue

if TYPE_CHECKING:
    from app.models.feature.snapshot import FeatureSnapshot


class FeatureDefinition(Base):
    """
    Master list of every supported feature.
    """

    __tablename__ = "feature_definitions"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    data_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        String(255),
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

    historical_feature_values: Mapped[list["FeatureValue"]] = relationship(
        "FeatureValue",
        back_populates="feature_definition",
        cascade="all, delete-orphan",
    )

    feature_snapshots: Mapped[list["FeatureSnapshot"]] = relationship(
        "FeatureSnapshot",
        back_populates="feature_definition",
        cascade="all, delete-orphan",
    )
