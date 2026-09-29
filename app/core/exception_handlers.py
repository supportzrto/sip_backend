from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.auth.exceptions import (
    AccountDisabledError,
    EmailAlreadyExistsError,
    ExpiredTokenError,
    InvalidCredentialsError,
    InvalidCurrentPasswordError,
    InvalidRefreshTokenError,
    InvalidTokenError,
    PermissionDeniedError,
    RateLimitExceededError,
)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(EmailAlreadyExistsError)
    async def email_exists_handler(
        request: Request,
        exc: EmailAlreadyExistsError,
    ):
        return JSONResponse(
            status_code=409,
            content={
                "detail": str(exc),
            },
        )

    @app.exception_handler(InvalidCredentialsError)
    async def invalid_credentials_handler(
        request: Request,
        exc: InvalidCredentialsError,
    ):
        return JSONResponse(
            status_code=401,
            content={
                "detail": str(exc),
            },
        )

    @app.exception_handler(InvalidTokenError)
    async def invalid_token_handler(
        request: Request,
        exc: InvalidTokenError,
    ):
        return JSONResponse(
            status_code=401,
            content={
                "detail": str(exc),
            },
        )

    @app.exception_handler(ExpiredTokenError)
    async def expired_token_handler(
        request: Request,
        exc: ExpiredTokenError,
    ):
        return JSONResponse(
            status_code=401,
            content={
                "detail": str(exc),
            },
        )

    @app.exception_handler(InvalidRefreshTokenError)
    async def invalid_refresh_token_handler(
        request: Request,
        exc: InvalidRefreshTokenError,
    ):
        return JSONResponse(
            status_code=401,
            content={
                "detail": str(exc),
            },
        )

    @app.exception_handler(PermissionDeniedError)
    async def permission_denied_handler(
        request: Request,
        exc: PermissionDeniedError,
    ):
        return JSONResponse(
            status_code=403,
            content={
                "detail": str(exc),
            },
        )

    @app.exception_handler(InvalidCurrentPasswordError)
    async def invalid_current_password_handler(
        request: Request,
        exc: InvalidCurrentPasswordError,
    ):
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc)},
        )

    @app.exception_handler(AccountDisabledError)
    async def account_disabled_handler(
        request: Request,
        exc: AccountDisabledError,
    ):
        return JSONResponse(
            status_code=403,
            content={
                "detail": str(exc),
            },
        )

    @app.exception_handler(RateLimitExceededError)
    async def rate_limit_exceeded_handler(
        request: Request,
        exc: RateLimitExceededError,
    ):
        return JSONResponse(
            status_code=429,
            content={
                "detail": str(exc),
            },
        )