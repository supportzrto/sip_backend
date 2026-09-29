from app.indicators.algorithms import calculate_atr
from app.indicators.base import Indicator
from app.indicators.enums import IndicatorType
from app.indicators.schemas import ATRValue
from app.market_data.schemas import HistoricalCandle


class ATRIndicator(Indicator):
    """
    Average True Range (ATR).
    """

    def __init__(
        self,
        period: int = 14,
    ):
        super().__init__(period)

    @property
    def indicator_type(self) -> IndicatorType:
        return IndicatorType.ATR

    def calculate(
        self,
        candles: list[HistoricalCandle],
    ) -> list[ATRValue]:

        if not self.has_enough_candles(candles):
            return []

        atr_values = calculate_atr(
            candles,
            self.period,
        )

        results: list[ATRValue] = []

        for candle, value in zip(
            candles[self.period:],
            atr_values,
        ):
            results.append(
                ATRValue(
                    symbol=candle.symbol,
                    trade_date=candle.trade_date,
                    indicator=self.indicator_type,
                    period=self.period,
                    value=value,
                )
            )

        return results