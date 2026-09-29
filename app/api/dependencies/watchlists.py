from fastapi import Depends
from sqlalchemy.orm import Session

from app.api.dependencies.database import get_db
from app.repositories.instrument_repository import InstrumentRepository
from app.repositories.watchlist_repository import WatchlistRepository


def get_watchlist_repository(
    db: Session = Depends(get_db),
) -> WatchlistRepository:

    return WatchlistRepository(db)


def get_instrument_repository(
    db: Session = Depends(get_db),
) -> InstrumentRepository:

    return InstrumentRepository(db)