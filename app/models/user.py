from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import relationship
from app.auth.constants import UserRole, UserStatus
from app.database.base import Base
from app.models.mixins.timestamp import TimestampMixin
from app.models.mixins.uuid import UUIDMixin
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.refresh_token import RefreshToken


class User(
    Base,
    UUIDMixin,
    TimestampMixin,
):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    full_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    role: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=UserRole.USER.value,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=UserStatus.ACTIVE.value,
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
