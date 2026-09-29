from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database.base import Base


class ScanRun(Base):
    __tablename__ = "scan_runs"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Nullable: scan runs persisted before ownership tracking was
    # added have no user to attribute them to, and a user's runs
    # should survive their account being deleted (see the
    # ON DELETE SET NULL migration) rather than being wiped out.
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    strategy: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    stocks_scanned: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    matches_found: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    results = relationship(
        "ScanResult",
        back_populates="scan_run",
        cascade="all, delete-orphan",
    )