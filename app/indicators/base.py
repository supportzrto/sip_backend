from abc import ABC, abstractmethod

from app.indicators.enums import IndicatorType
from app.indicators.schemas import IndicatorValue
from app.market_data.schemas import HistoricalCandle


class Indicator(ABC):
    """
    Base class for all technical indicators.
    """

    def __init__(
        self,
        period: int,
    ):
        self._validate_period(period)
        self.period = period

    @property
    @abstractmethod
    def indicator_type(self) -> IndicatorType:
        """
        Indicator type.
        """
        raise NotImplementedError

    @staticmethod
    def _validate_period(period: int) -> None:

        if period < 2:
            raise ValueError(
                "Indicator period must be at least 2."
            )

    def has_enough_candles(
        self,
        candles: list[HistoricalCandle],
    ) -> bool:

        return len(candles) >= self.period

    @abstractmethod
    def calculate(
        self,
        candles: list[HistoricalCandle],
    ) -> list[IndicatorValue]:
        """
        Calculate indicator values.
        """
        raise NotImplementedError