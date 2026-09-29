from app.indicators.algorithms import calculate_macd
from app.indicators.base import Indicator
from app.indicators.enums import IndicatorType
from app.indicators.schemas import MACDValue
from app.market_data.schemas import HistoricalCandle


class MACDIndicator(Indicator):
    """
    Moving Average Convergence Divergence (MACD).
    """

    def __init__(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ):
        super().__init__(slow_period)

        if fast_period >= slow_period:
            raise ValueError(
                "Fast period must be smaller than slow period."
            )

        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period

    @property
    def indicator_type(self) -> IndicatorType:
        return IndicatorType.MACD

    def calculate(
        self,
        candles: list[HistoricalCandle],
    ) -> list[MACDValue]:

        if len(candles) < self.slow_period:
            return []

        close_prices = [
            candle.close
            for candle in candles
        ]

        result = calculate_macd(
            close_prices,
            self.fast_period,
            self.slow_period,
            self.signal_period,
        )

        # First histogram corresponds to this candle
        start_index = (
            self.slow_period
            + self.signal_period
            - 2
        )

        results: list[MACDValue] = []

        for candle, macd, signal, histogram in zip(
            candles[start_index:],
            result.macd,
            result.signal,
            result.histogram,
        ):
            results.append(
                MACDValue(
                    symbol=candle.symbol,
                    trade_date=candle.trade_date,
                    indicator=self.indicator_type,
                    fast_period=self.fast_period,
                    slow_period=self.slow_period,
                    signal_period=self.signal_period,
                    macd=macd,
                    signal=signal,
                    histogram=histogram,
                )
            )

        return results