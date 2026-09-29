from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins.timestamp import TimestampMixin
from app.models.mixins.uuid import UUIDMixin


class RefreshToken(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    token_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    is_revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    user = relationship("User", back_populates="refresh_tokens")