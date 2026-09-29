from decimal import Decimal

from app.indicators.algorithms import calculate_bollinger_bands
from app.indicators.base import Indicator
from app.indicators.enums import IndicatorType
from app.indicators.schemas import BollingerBandsValue
from app.market_data.schemas import HistoricalCandle


class BollingerBandsIndicator(Indicator):
    """
    Bollinger Bands.
    """

    def __init__(
        self,
        period: int = 20,
        multiplier: int = 2,
    ):
        super().__init__(period)

        self.multiplier = Decimal(str(multiplier))

    @property
    def indicator_type(self) -> IndicatorType:
        return IndicatorType.BOLLINGER

    def calculate(
        self,
        candles: list[HistoricalCandle],
    ) -> list[BollingerBandsValue]:

        if not self.has_enough_candles(candles):
            return []

        close_prices = [
            candle.close
            for candle in candles
        ]

        bands = calculate_bollinger_bands(
            close_prices,
            self.period,
            self.multiplier,
        )

        results: list[BollingerBandsValue] = []

        for candle, middle, upper, lower in zip(
            candles[self.period - 1:],
            bands.middle,
            bands.upper,
            bands.lower,
        ):
            results.append(
                BollingerBandsValue(
                    symbol=candle.symbol,
                    trade_date=candle.trade_date,
                    indicator=self.indicator_type,
                    period=self.period,
                    upper=upper,
                    middle=middle,
                    lower=lower,
                )
            )

        return results