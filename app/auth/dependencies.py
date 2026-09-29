from collections.abc import Callable
from uuid import UUID

from fastapi import Depends
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from sqlalchemy.orm import Session

from app.auth.constants import UserRole
from app.auth.exceptions import (
    InvalidTokenError,
    PermissionDeniedError,
)
from app.auth.jwt import decode_access_token
from app.auth.repository import UserRepository
from app.database.session import get_db
from app.models.user import User
from app.auth.constants import UserRole, UserStatus
from app.auth.exceptions import AccountDisabledError


security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:

    payload = decode_access_token(
        credentials.credentials
    )

    try:
        user_uuid = UUID(payload["sub"])
    except (KeyError, ValueError, TypeError) as exc:
        raise InvalidTokenError(
            "Invalid access token."
        ) from exc

    repository = UserRepository(db)

    user = repository.get_by_uuid(user_uuid)

    if user is None:
        raise InvalidTokenError(
            "Invalid access token."
        )

    if user.status != UserStatus.ACTIVE.value:
        raise AccountDisabledError(
            "Your account is not active."
    )

    return user


def require_roles(
    *allowed_roles: UserRole,
) -> Callable:

    allowed_values = {
        role.value for role in allowed_roles
    }

    def dependency(
        current_user: User = Depends(get_current_user),
    ) -> User:

        if current_user.role not in allowed_values:
            raise PermissionDeniedError(
                "You do not have permission to access this resource."
            )

        return current_user

    return dependency


require_admin = require_roles(
    UserRole.ADMIN,
)


require_user = require_roles(
    UserRole.USER,
    UserRole.ADMIN,
)