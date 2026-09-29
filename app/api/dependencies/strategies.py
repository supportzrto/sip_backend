from fastapi import Depends
from sqlalchemy.orm import Session

from app.api.dependencies.database import get_db
from app.repositories.saved_strategy_repository import (
    SavedStrategyRepository,
)


def get_saved_strategy_repository(
    db: Session = Depends(get_db),
) -> SavedStrategyRepository:

    return SavedStrategyRepository(db)