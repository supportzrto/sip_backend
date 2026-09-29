from decimal import Decimal

from app.indicators.algorithms import (
    calculate_atr,
    calculate_basic_bands,
    calculate_final_bands,
    calculate_supertrend,
)
from app.indicators.base import Indicator
from app.indicators.enums import IndicatorType
from app.indicators.schemas import SupertrendValue
from app.market_data.schemas import HistoricalCandle


class SupertrendIndicator(Indicator):
    """
    Supertrend Indicator.
    """

    def __init__(
        self,
        period: int = 10,
        multiplier: int = 3,
    ):
        super().__init__(period)

        self.multiplier = Decimal(str(multiplier))

    @property
    def indicator_type(self) -> IndicatorType:
        return IndicatorType.SUPERTREND

    def calculate(
        self,
        candles: list[HistoricalCandle],
    ) -> list[SupertrendValue]:

        if not self.has_enough_candles(candles):
            return []

        atr = calculate_atr(
            candles,
            self.period,
        )

        basic = calculate_basic_bands(
            candles,
            atr,
            self.period,
            self.multiplier,
        )

        final = calculate_final_bands(
            candles,
            basic,
            self.period,
        )

        trend = calculate_supertrend(
            candles,
            final,
            self.period,
        )

        results: list[SupertrendValue] = []

        for candle, value, bullish in zip(
            candles[self.period:],
            trend.values,
            trend.bullish,
        ):

            results.append(
                SupertrendValue(
                    symbol=candle.symbol,
                    trade_date=candle.trade_date,
                    indicator=self.indicator_type,
                    period=self.period,
                    multiplier=self.multiplier,
                    value=value,
                    is_bullish=bullish,
                )
            )

        return results