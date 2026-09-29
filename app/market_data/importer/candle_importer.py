from app.market_data.providers.base import MarketDataProvider
from app.market_data.validators.candle_validator import CandleValidator
from app.models.daily_candle import DailyCandle
from app.repositories.daily_candle_repository import (
    DailyCandleRepository,
)
from app.repositories.instrument_repository import (
    InstrumentRepository,
)

from app.market_data.logger import MarketDataLogger


BATCH_SIZE = 1000


class HistoricalDataImporter:
    """
    Imports historical daily candles into the database.
    """

    

    def __init__(
        self,
        provider: MarketDataProvider,
        instrument_repository: InstrumentRepository,
        candle_repository: DailyCandleRepository,
    ):
        self.provider = provider
        self.instrument_repository = instrument_repository
        self.candle_repository = candle_repository

    def import_daily_candles(
        self,
        symbol: str,
    ) -> int:
        """
        Import historical candles for a single instrument.

        Returns:
            int: Number of imported candles.
        """

        instrument = self.instrument_repository.get_by_symbol(symbol)

        if instrument is None:
            raise ValueError(
                f"Instrument '{symbol}' not found."
            )

        historical_candles = self.provider.fetch_daily_candles(symbol)

        print(
            f"Provider returned {len(historical_candles)} candles"
        )

        self.logger = MarketDataLogger()

        batch: list[DailyCandle] = []
        imported = 0
        skipped = 0

        for candle in historical_candles:

            try:
                CandleValidator.validate(candle)
            
            except ValueError as e:
                skipped += 1
                self.logger.log_invalid_candle(
                    candle.symbol,
                    candle.trade_date,
                    str(e),
                )

                continue

            batch.append(
                DailyCandle(
                    instrument_id=instrument.id,
                    trade_date=candle.trade_date,
                    open=candle.open,
                    high=candle.high,
                    low=candle.low,
                    close=candle.close,
                    volume=candle.volume,
                )
            )

            # Save every batch of 1000 candles
            if len(batch) >= BATCH_SIZE:

                self.candle_repository.save_many(batch)
                self.candle_repository.commit()

                imported += len(batch)

                batch.clear()

        # Save remaining candles
        if batch:

            self.candle_repository.save_many(batch)
            self.candle_repository.commit()

            print(
                f"Imported: {imported} | "
                f"Skipped: {skipped}"
            )

            imported += len(batch)

        return imported