
from app.services.historical_instrument_processor import (
    HistoricalInstrumentProcessor,
)


class HistoricalLoader:
    """
    Loads historical feature values
    for every instrument.
    """

    def __init__(
        self,
        processor: HistoricalInstrumentProcessor,
    ):

        self.processor = processor

    def load(
        self,
        instruments,
        candle_provider,
    ) -> int:

        total_rows = 0

        for instrument in instruments:

            candles = candle_provider.load_history(
                instrument.symbol
            )

            total_rows += self.processor.process(
                instrument.id,
                candles,
            )

        return total_rows