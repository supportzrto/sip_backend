from datetime import date
from abc import ABC, abstractmethod

from app.market_data.schemas import (
    HistoricalCandle,
    HistoricalInstrument,
)


class MarketDataProvider(ABC):

    @abstractmethod
    def fetch_instruments(self) -> list[HistoricalInstrument]:
        raise NotImplementedError

    @abstractmethod
    def fetch_daily_candles(
        self,
        symbol: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[HistoricalCandle]:
        raise NotImplementedError