from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy import delete,update
from datetime import datetime, timezone
from app.models.refresh_token import RefreshToken


class RefreshTokenRepository:

    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        refresh_token: RefreshToken,
    ) -> RefreshToken:

        self.session.add(refresh_token)
        self.session.flush()

        return refresh_token

    def get_by_hash(
        self,
        token_hash: str,
    ) -> RefreshToken | None:

        stmt = (
            select(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
        )

        return self.session.scalar(stmt)

    def revoke(
        self,
        refresh_token: RefreshToken,
    ) -> None:

        refresh_token.is_revoked = True

        self.session.flush()

    def revoke_all_for_user(self, user_id: int) -> None:

        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.is_revoked.is_(False),
            )
            .values(is_revoked=True)
        )

        self.session.execute(stmt)

    def revoke(
        self,
        refresh_token: RefreshToken,
    ) -> None:
        refresh_token.is_revoked = True
        self.session.flush()


    def delete_expired(self) -> None:
        

        stmt = delete(RefreshToken).where(
            RefreshToken.expires_at < datetime.now(timezone.utc)
        )

        self.session.execute(stmt)

    