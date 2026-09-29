from sqlalchemy import select

from app.models.instrument import Instrument
from app.models.watchlist import Watchlist
from app.models.watchlist_item import WatchlistItem
from app.repositories.base_repository import BaseRepository


class WatchlistRepository(BaseRepository):

    def create(self, watchlist: Watchlist) -> Watchlist:

        self.add(watchlist)
        self.db.flush()

        return watchlist

    def list_for_user(self, user_id: int) -> list[Watchlist]:

        statement = (
            select(Watchlist)
            .where(Watchlist.user_id == user_id)
            .order_by(Watchlist.name)
        )

        return list(self.db.scalars(statement).all())

    def get_by_id(
        self,
        watchlist_id: int,
        user_id: int | None = None,
    ) -> Watchlist | None:
        """
        user_id=None returns the watchlist regardless of owner (for
        internal/scheduler use). Pass the requesting user's id to
        additionally require they own it -- a mismatch returns None,
        which callers should treat the same as "not found".
        """

        statement = select(Watchlist).where(Watchlist.id == watchlist_id)

        if user_id is not None:
            statement = statement.where(Watchlist.user_id == user_id)

        return self.db.scalar(statement)

    def delete(self, watchlist: Watchlist) -> None:

        self.db.delete(watchlist)

    def get_item(
        self,
        watchlist_id: int,
        instrument_id: int,
    ) -> WatchlistItem | None:

        statement = select(WatchlistItem).where(
            WatchlistItem.watchlist_id == watchlist_id,
            WatchlistItem.instrument_id == instrument_id,
        )

        return self.db.scalar(statement)

    def add_item(self, item: WatchlistItem) -> WatchlistItem:

        self.add(item)
        self.db.flush()

        return item

    def remove_item(self, item: WatchlistItem) -> None:

        self.db.delete(item)

    def get_symbols(self, watchlist_id: int) -> list[str]:
        """
        The symbols currently on a watchlist -- what AlertService
        scopes a watchlist-bound alert's scan to.
        """

        statement = (
            select(Instrument.symbol)
            .join(
                WatchlistItem,
                WatchlistItem.instrument_id == Instrument.id,
            )
            .where(WatchlistItem.watchlist_id == watchlist_id)
        )

        return list(self.db.scalars(statement).all())