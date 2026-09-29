from decimal import Decimal

from app.indicators.algorithms import calculate_volume_surge
from app.indicators.base import Indicator
from app.indicators.enums import IndicatorType
from app.indicators.schemas import IndicatorValue
from app.market_data.schemas import HistoricalCandle


class VolumeSurgeIndicator(Indicator):
    """
    Ratio of today's volume to the average volume over the prior
    `period` days. Used as breakout/breakdown confirmation -- a
    price move on unusually high volume is a stronger signal than
    the same move on ordinary volume.
    """

    def __init__(self, period: int):
        super().__init__(period)

    @property
    def indicator_type(self) -> IndicatorType:
        return IndicatorType.VOLUME_SURGE

    def calculate(
        self,
        candles: list[HistoricalCandle],
    ) -> list[IndicatorValue]:

        if len(candles) <= self.period:
            return []

        volumes = [
            Decimal(candle.volume)
            for candle in candles
        ]

        values = calculate_volume_surge(
            volumes,
            self.period,
        )

        results: list[IndicatorValue] = []

        for candle, value in zip(candles[self.period:], values):

            results.append(
                IndicatorValue(
                    symbol=candle.symbol,
                    trade_date=candle.trade_date,
                    indicator=self.indicator_type,
                    period=self.period,
                    value=value,
                )
            )

        return results