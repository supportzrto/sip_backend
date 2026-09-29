from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    """
    Repository for User.
    """

    def __init__(
        self,
        session: Session,
    ):
        self.session = session

    def get_by_id(
        self,
        user_id: int,
    ) -> User | None:

        statement = (
            select(User)
            .where(User.id == user_id)
        )

        return self.session.scalar(statement)

    def get_by_uuid(
        self,
        user_uuid: UUID,
    ) -> User | None:

        statement = (
            select(User)
            .where(User.uuid == user_uuid)
        )

        return self.session.scalar(statement)

    def get_by_email(
        self,
        email: str,
    ) -> User | None:

        statement = (
            select(User)
            .where(User.email == email)
        )

        return self.session.scalar(statement)

    def exists_by_email(
        self,
        email: str,
    ) -> bool:

        return (
            self.get_by_email(email)
            is not None
        )

    def create(
        self,
        user: User,
    ) -> User:

        self.session.add(user)

        self.session.flush()

        return user

    def delete(
        self,
        user: User,
    ) -> None:

        self.session.delete(user)