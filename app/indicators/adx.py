from app.indicators.algorithms import calculate_adx
from app.indicators.base import Indicator
from app.indicators.enums import IndicatorType
from app.indicators.schemas import ADXValue
from app.market_data.schemas import HistoricalCandle


class ADXIndicator(Indicator):
    """
    Average Directional Index (ADX).
    """

    def __init__(
        self,
        period: int = 14,
    ):
        super().__init__(period)

    @property
    def indicator_type(self) -> IndicatorType:
        return IndicatorType.ADX

    def calculate(
        self,
        candles: list[HistoricalCandle],
    ) -> list[ADXValue]:

        if not self.has_enough_candles(candles):
            return []

        adx_values = calculate_adx(
            candles,
            self.period,
        )

        # ADX starts after:
        # period TR values
        # +
        # period DX smoothing
        start_index = (self.period * 2) - 1

        results: list[ADXValue] = []

        for candle, value in zip(
            candles[start_index:],
            adx_values,
        ):
            results.append(
                ADXValue(
                    symbol=candle.symbol,
                    trade_date=candle.trade_date,
                    indicator=self.indicator_type,
                    period=self.period,
                    value=value,
                )
            )

        return results