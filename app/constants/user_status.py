from enum import StrEnum


class UserStatus(StrEnum):
    ACTIVE = "ACTIVE"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    SUSPENDED = "SUSPENDED"
    DELETED = "DELETED"