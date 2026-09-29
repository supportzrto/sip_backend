from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.auth.exceptions import (
    EmailAlreadyExistsError,
    ExpiredTokenError,
    InvalidCredentialsError,
    InvalidCurrentPasswordError,
    InvalidRefreshTokenError,
    InvalidTokenError,
)
from app.auth.jwt import (
    create_access_token,
)
from app.auth.refresh_token_repository import RefreshTokenRepository
from app.auth.security import generate_refresh_token
from app.auth.repository import UserRepository
from app.auth.schemas import TokenResponse
from app.auth.security import (
    generate_secure_token,
    hash_password,
    verify_password,
)

from app.auth.jwt import (
    decode_refresh_token,
)
from app.auth.utils import hash_refresh_token
from app.config.settings import settings
from app.core.email import EmailDeliveryError, send_password_reset_email
from app.models.password_reset_token import PasswordResetToken
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.auth.constants import UserStatus
from app.auth.exceptions import AccountDisabledError
from app.auth.rate_limiter import check_rate_limit, reset_attempts
from app.auth.password_reset_repository import PasswordResetRepository
from app.auth.security import generate_secure_token

class AuthService:
    """
    Business logic for authentication.
    """

    def __init__(
        self,
        session: Session,
    ):
        self.session = session
        self.user_repository = UserRepository(session)
        self.refresh_token_repository = RefreshTokenRepository(session)
        self.repository = UserRepository(session)
        self.refresh_token_repository = RefreshTokenRepository(session)
        self.password_reset_repository = PasswordResetRepository(session)

    def register(
        self,
        *,
        full_name: str,
        email: str,
        password: str,
    ) -> User:
        """
        Register a new user.
        """

        if self.user_repository.exists_by_email(email):
            raise EmailAlreadyExistsError(f"Email '{email}' is already registered.")

        password_hash = hash_password(password)

        user = User(
            full_name=full_name,
            email=email,
            password_hash=password_hash,
        )

        self.user_repository.create(user)

        self.session.commit()
        self.session.refresh(user)

        return user

    def login(
        self,
        *,
        email: str,
        password: str,
    ) -> TokenResponse:
        """
        Authenticate a user and issue access + refresh tokens.
        """

        key = email

        check_rate_limit(key)

        user = self.user_repository.get_by_email(email)

        if user is None:
            raise InvalidCredentialsError("Invalid email or password.")

        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsError("Invalid email or password.")

        if user.status != UserStatus.ACTIVE.value:
            raise AccountDisabledError(
                "Your account is not active."
            )

        # Update last login time
        user.last_login_at = datetime.now(timezone.utc)

        # Generate JWTs
        access_token = create_access_token(user.uuid)
        refresh_token = generate_refresh_token()

        # Store hashed refresh token
        refresh_token_record = RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        )

        self.refresh_token_repository.create(refresh_token_record)

        # Commit everything in one transaction
        self.session.commit()

        # A successful login clears the failed-attempt counter for
        # this key -- otherwise a user who mistypes their password a
        # few times, then logs in correctly, would still get rate
        # limited later purely from attempts that already succeeded.
        reset_attempts(key)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )


    def refresh(
        self,
        *,
        refresh_token: str,
    ) -> TokenResponse:

    #  Hash token
        token_hash = hash_refresh_token(refresh_token)

    #  Get token from DB
        stored = self.refresh_token_repository.get_by_hash(token_hash)

        if not stored:
           raise InvalidCredentialsError("Invalid refresh token.")

        if stored.is_revoked:
           raise InvalidCredentialsError("Refresh token has been revoked.")

        if stored.expires_at < datetime.now(timezone.utc):
           raise InvalidCredentialsError("Refresh token has expired.")

        user = stored.user

    #  Check user status
        if user.status != UserStatus.ACTIVE.value:
            raise AccountDisabledError("Your account is not active.")

    #  ROTATE TOKEN (IMPORTANT)
        stored.is_revoked = True

    #  Create new tokens
        new_access_token = create_access_token(user.uuid)

        new_refresh_raw = generate_refresh_token()
        new_refresh_hash = hash_refresh_token(new_refresh_raw)

    #  Save new refresh token
        new_refresh = RefreshToken(
            user_id=user.id,
            token_hash=new_refresh_hash,
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        )

        self.refresh_token_repository.create(new_refresh)

        self.session.commit()

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_raw,
        )

    def logout(
        self,
        *,
        refresh_token: str,
    ) -> None:
        token_hash = hash_refresh_token(refresh_token)

        stored_token = (
            self.refresh_token_repository.get_by_hash(
                token_hash
            )
        )

        if not stored_token:
           return
        
        

        if stored_token is None:
            raise InvalidRefreshTokenError(
                "Invalid refresh token."
            )

        if stored_token.is_revoked:
            raise InvalidRefreshTokenError(
                "Refresh token has already been revoked."
            )

        self.refresh_token_repository.revoke(
            stored_token
        )

        self.session.commit()

    def change_password(
        self,
        *,
        user: User,
        current_password: str,
        new_password: str,
    ) -> None:

        if not verify_password(
            current_password,
            user.password_hash,
        ):
            raise InvalidCurrentPasswordError(
                "Current password is incorrect."
            )

        if verify_password(
            new_password,
            user.password_hash,
        ):
            raise InvalidCurrentPasswordError(
                "New password must be different from the current password."
            )

        user.password_hash = hash_password(new_password)

        self.refresh_token_repository.revoke_all_for_user(
            user.id
        )

        self.session.commit()

    def logout_all(
        self,
        *,
        user: User,
    ) -> None:

        self.refresh_token_repository.revoke_all_for_user(
            user.id
        )

        self.session.commit()

    def forgot_password(self, *, email: str) -> None:

        user = self.repository.get_by_email(email)

        if not user:
            return  # DO NOT reveal email existence

        raw_token = generate_secure_token()
        token_hash = hash_refresh_token(raw_token)

        reset_token = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
             used=False,
        )

        self.password_reset_repository.create(reset_token)
        self.session.commit()

        reset_link = (
            f"{settings.FRONTEND_URL.rstrip('/')}"
            f"{settings.PASSWORD_RESET_PATH}"
            f"?token={raw_token}"
        )

        try:
            send_password_reset_email(
                to=user.email,
                full_name=user.full_name,
                reset_link=reset_link,
            )
        except EmailDeliveryError:
            # The reset token is already committed and still valid
            # for its full 15-minute window -- a delivery failure
            # here shouldn't fail the request (and, consistent with
            # not revealing whether the account exists, the caller
            # gets the same generic response either way). send_email
            # already logged the failure for an operator to notice.
            pass


    def reset_password(
        self,
        *,
        token: str,
        new_password: str,
    ) -> None:

        token_hash = hash_refresh_token(token)

        stored = self.password_reset_repository.get_by_hash(token_hash)

        if not stored:
            raise InvalidTokenError("Invalid token")

        if stored.used:
            raise InvalidTokenError("Token already used")

        expires_at = stored.expires_at

        # Defensive: some DB backends (notably SQLite, used in the
        # test suite) don't round-trip tzinfo on a
        # DateTime(timezone=True) column, returning a naive
        # datetime. Treat a naive value as UTC (what it was written
        # as) rather than letting the comparison below raise.
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at < datetime.now(timezone.utc):
            raise ExpiredTokenError("Token expired")

        user = stored.user

        user.password_hash = hash_password(new_password)

        stored.used = True

        self.refresh_token_repository.revoke_all_for_user(user.id)

        self.session.commit()