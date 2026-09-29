from app.indicators.algorithms import calculate_sma
from app.indicators.base import Indicator
from app.indicators.enums import IndicatorType
from app.indicators.schemas import IndicatorValue
from app.market_data.schemas import HistoricalCandle


class SMAIndicator(Indicator):
    """
    Simple Moving Average (SMA).
    """

    def __init__(
        self,
        period: int,
    ):
        super().__init__(period)

    @property
    def indicator_type(self) -> IndicatorType:
        return IndicatorType.SMA

    def calculate(
        self,
        candles: list[HistoricalCandle],
    ) -> list[IndicatorValue]:
        """
        Calculate the Simple Moving Average (SMA).
        """

        if not self.has_enough_candles(candles):
            return []

        # Extract close prices
        close_prices = [
            candle.close
            for candle in candles
        ]

        # Calculate SMA values
        sma_values = calculate_sma(
            close_prices,
            self.period,
        )

        # Convert to IndicatorValue objects
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