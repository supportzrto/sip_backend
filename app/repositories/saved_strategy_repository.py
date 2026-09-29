from sqlalchemy import select

from app.models.saved_strategy import SavedStrategy
from app.repositories.base_repository import BaseRepository


class SavedStrategyRepository(BaseRepository):

    def create(self, saved_strategy: SavedStrategy) -> SavedStrategy:

        self.add(saved_strategy)
        self.db.flush()

        return saved_strategy

    def list_for_user(self, user_id: int) -> list[SavedStrategy]:

        statement = (
            select(SavedStrategy)
            .where(SavedStrategy.user_id == user_id)
            .order_by(SavedStrategy.name)
        )

        return list(self.db.scalars(statement).all())

    def get_by_id(
        self,
        saved_strategy_id: int,
        user_id: int | None = None,
    ) -> SavedStrategy | None:
        """
        user_id=None returns the strategy regardless of owner (for
        internal/scheduler use -- an alert rule referencing this
        strategy may be evaluated on someone else's behalf by the
        scheduler, not through a request from its owner). Pass the
        requesting user's id to additionally require they own it --
        a mismatch returns None, which callers should treat the same
        as "not found".
        """

        statement = select(SavedStrategy).where(
            SavedStrategy.id == saved_strategy_id,
        )

        if user_id is not None:
            statement = statement.where(SavedStrategy.user_id == user_id)

        return self.db.scalar(statement)

    def delete(self, saved_strategy: SavedStrategy) -> None:

        self.db.delete(saved_strategy)