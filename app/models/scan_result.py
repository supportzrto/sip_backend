from __future__ import annotations

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class ScanResult(Base):
    __tablename__ = "scan_results"

    id: Mapped[int] = mapped_column(primary_key=True)

    scan_run_id: Mapped[int] = mapped_column(
        ForeignKey("scan_runs.id"),
        nullable=False,
        index=True,
    )

    instrument_id: Mapped[int] = mapped_column(
        ForeignKey("instruments.id"),
        nullable=False,
        index=True,
    )

    # Denormalized so scan history stays readable/stable even
    # if the instrument's symbol changes later.
    symbol: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    # Human-readable explanations for why this stock matched
    # (e.g. "EMA20 crossed above EMA50 (105.00 vs 100.00)").
    reasons: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    scan_run = relationship(
        "ScanRun",
        back_populates="results",
    )

    instrument = relationship(
        "Instrument",
    )