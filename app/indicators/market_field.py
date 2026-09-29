from collections.abc import Callable
from decimal import Decimal

from app.indicators.enums import IndicatorType
from app.indicators.schemas import RawFieldValue
from app.market_data.schemas import HistoricalCandle


class MarketFieldIndicator:
    """
    Not a computed indicator -- just extracts a raw OHLCV field
    (open/high/low/close/volume) from each candle directly, tagged
    with the given IndicatorType, so it can flow through the same
    feature-store pipeline (registry -> service -> builder -> mapper)
    as real indicators and be referenced in scan conditions the same
    way (e.g. "CLOSE crosses_above HIGHEST252").

    Deliberately does not inherit from the period-based Indicator
    base class -- there's no period here, no warm-up requirement,
    and no computation, just a field lookup.
    """

    def __init__(
        self,
        indicator_type: IndicatorType,
        extractor: Callable[[HistoricalCandle], Decimal | int],
    ):
        self.indicator_type = indicator_type
        self._extractor = extractor

    def calculate(
        self,
        candles: list[HistoricalCandle],
    ) -> list[RawFieldValue]:

        return [
            RawFieldValue(
                symbol=candle.symbol,
                trade_date=candle.trade_date,
                field=self.indicator_type.value,
                value=Decimal(self._extractor(candle)),
            )
            for candle in candles
        ]