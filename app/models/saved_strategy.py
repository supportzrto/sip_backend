from datetime import datetime, UTC

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class SavedStrategy(Base):
    """
    A user's own custom scan expression tree, saved under a name so
    it can be reused -- run directly via /strategies/{id}/scan, or
    referenced by an AlertRule -- without resubmitting the full
    expression JSON every time.

    expression stores a serialized app.scanner.schemas.ScanExpression
    (the same structure /scanner/scan accepts inline). It's kept as
    a plain JSON blob rather than normalized into condition rows:
    the tree is only ever read/written as a whole (never queried by
    its internal fields), so normalizing it would add joins with no
    corresponding benefit.
    """

    __tablename__ = "saved_strategies"

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

    expression: Mapped[dict] = mapped_column(
        JSON,
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

    __table_args__ = (
        UniqueConstraint(
            "user_id", "name", name="uq_saved_strategy_user_name",
        ),
    )