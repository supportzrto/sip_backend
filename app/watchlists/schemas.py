from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WatchlistCreate(BaseModel):

    name: str = Field(min_length=1, max_length=100)


class WatchlistItemCreate(BaseModel):
    """
    Add a symbol to a watchlist. The symbol must already exist as a
    synced instrument -- watchlists track instruments this platform
    actually has data for, not arbitrary tickers.
    """

    symbol: str = Field(min_length=1)


class WatchlistItemResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: int

    symbol: str

    added_at: datetime


class WatchlistResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: int

    user_id: int

    name: str

    created_at: datetime

    items: list[WatchlistItemResponse]


class WatchlistListResponse(BaseModel):

    model_config = ConfigDict(frozen=True)

    watchlists: list[WatchlistResponse]