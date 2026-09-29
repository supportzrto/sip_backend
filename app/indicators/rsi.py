from app.indicators.algorithms import calculate_rsi
from app.indicators.base import Indicator
from app.indicators.enums import IndicatorType
from app.indicators.schemas import RSIValue
from app.market_data.schemas import HistoricalCandle


class RSIIndicator(Indicator):
    """
    Relative Strength Index (RSI).
    """

    def __init__(
        self,
        period: int = 14,
    ):
        super().__init__(period)

    @property
    def indicator_type(self) -> IndicatorType:
        return IndicatorType.RSI

    def calculate(
        self,
        candles: list[HistoricalCandle],
    ) -> list[RSIValue]:

        if not self.has_enough_candles(candles):
            return []

        close_prices = [
            candle.close
            for candle in candles
        ]

        rsi_values = calculate_rsi(
            close_prices,
            self.period,
        )

        results: list[RSIValue] = []

        for candle, value in zip(
            candles[self.period:],
            rsi_values,
        ):
            results.append(
                RSIValue(
                    symbol=candle.symbol,
                    trade_date=candle.trade_date,
                    indicator=self.indicator_type,
                    period=self.period,
                    value=value,
                )
            )

        return results