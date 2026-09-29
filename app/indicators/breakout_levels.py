from app.indicators.algorithms import (
    calculate_rolling_max_lagged,
    calculate_rolling_min_lagged,
)
from app.indicators.base import Indicator
from app.indicators.enums import IndicatorType
from app.indicators.schemas import IndicatorValue
from app.market_data.schemas import HistoricalCandle


class HighestHighIndicator(Indicator):
    """
    Highest high over the prior `period` days (lagged -- does not
    include the current day). The classic breakout reference level:
    a close crossing above this is a new N-day high breakout.
    """

    def __init__(self, period: int):
        super().__init__(period)

    @property
    def indicator_type(self) -> IndicatorType:
        return IndicatorType.HIGHEST

    def calculate(
        self,
        candles: list[HistoricalCandle],
    ) -> list[IndicatorValue]:

        if len(candles) <= self.period:
            return []

        highs = [candle.high for candle in candles]

        values = calculate_rolling_max_lagged(
            highs,
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


class LowestLowIndicator(Indicator):
    """
    Lowest low over the prior `period` days (lagged -- does not
    include the current day). The breakdown mirror of
    HighestHighIndicator.
    """

    def __init__(self, period: int):
        super().__init__(period)

    @property
    def indicator_type(self) -> IndicatorType:
        return IndicatorType.LOWEST

    def calculate(
        self,
        candles: list[HistoricalCandle],
    ) -> list[IndicatorValue]:

        if len(candles) <= self.period:
            return []

        lows = [candle.low for candle in candles]

        values = calculate_rolling_min_lagged(
            lows,
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