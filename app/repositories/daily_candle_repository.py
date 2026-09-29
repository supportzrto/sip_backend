from app.models.daily_candle import DailyCandle
from app.repositories.base_repository import BaseRepository


class DailyCandleRepository(BaseRepository):

    def save_many(
        self,
        candles: list[DailyCandle],
    ) -> None:
        self.add_many(candles)