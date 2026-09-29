from app.indicators.algorithms import calculate_ema
from app.indicators.base import Indicator
from app.indicators.enums import IndicatorType
from app.indicators.schemas import IndicatorValue
from app.market_data.schemas import HistoricalCandle
from app.indicators.algorithms import calculate_sma

class EMAIndicator(Indicator):
    """
    Exponential Moving Average (EMA).
    """

    def __init__(
        self,
        period: int,
    ):
        super().__init__(period)

    @property
    def indicator_type(self) -> IndicatorType:
        return IndicatorType.EMA

    def calculate(
        self,
        candles: list[HistoricalCandle],
    ) -> list[IndicatorValue]:
        """
        Calculate the Exponential Moving Average (EMA).
        """

        if not self.has_enough_candles(candles):
            return []

        close_prices = [
            candle.close
            for candle in candles
        ]

        sma_values = calculate_ema(
            close_prices,
            self.period,
        )

        results: list[IndicatorValue] = []

        for candle, value in zip(
            candles[self.period - 1 :],
            sma_values,
        ):
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