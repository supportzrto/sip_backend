from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.password_reset_token import PasswordResetToken


class PasswordResetRepository:

    def __init__(self, session: Session):
        self.session = session

    def create(self, token):
        self.session.add(token)
        self.session.flush()

    def get_by_hash(self, token_hash: str):
        stmt = select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash
        )
        return self.session.scalar(stmt)