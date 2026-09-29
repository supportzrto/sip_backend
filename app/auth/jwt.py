from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError

from app.auth.exceptions import (
    ExpiredTokenError,
    InvalidTokenError as AuthInvalidTokenError,
)
from app.config.settings import settings


def _create_token(
    *,
    user_uuid: UUID,
    token_type: str,
    expires_delta: timedelta,
) -> str:
    expires_at = datetime.now(timezone.utc) + expires_delta

    payload = {
        "sub": str(user_uuid),
        "type": token_type,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_access_token(user_uuid: UUID) -> str:
    return _create_token(
        user_uuid=user_uuid,
        token_type="access",
        expires_delta=timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
        ),
    )


def create_refresh_token(user_uuid: UUID) -> str:
    return _create_token(
        user_uuid=user_uuid,
        token_type="refresh",
        expires_delta=timedelta(
            days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS,
        ),
    )


def _decode_token(
    *,
    token: str,
    expected_type: str,
) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

    except ExpiredSignatureError as exc:
        raise ExpiredTokenError("Token has expired.") from exc

    except InvalidTokenError as exc:
        raise AuthInvalidTokenError("Invalid token.") from exc

    if payload.get("type") != expected_type:
        raise AuthInvalidTokenError(
            f"Expected {expected_type} token."
        )

    return payload


def decode_access_token(token: str) -> dict:
    return _decode_token(
        token=token,
        expected_type="access",
    )


def decode_refresh_token(token: str) -> dict:
    return _decode_token(
        token=token,
        expected_type="refresh",
    )