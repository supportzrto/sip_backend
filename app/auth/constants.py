from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "ADMIN"
    USER = "USER"


class UserStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    DELETED = "DELETED"