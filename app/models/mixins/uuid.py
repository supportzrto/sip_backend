import uuid as uuid_lib

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class UUIDMixin:
    uuid: Mapped[uuid_lib.UUID] = mapped_column(
        UUID(as_uuid=True),
        default=uuid_lib.uuid4,
        unique=True,
        nullable=False,
        index=True,
    )