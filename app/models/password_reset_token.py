from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins.timestamp import TimestampMixin
from app.models.mixins.uuid import UUIDMixin


class PasswordResetToken(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    token_hash: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    used: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
    )

    user = relationship("User")