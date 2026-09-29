from collections.abc import Sequence

from app.indicators.registry import IndicatorRegistry
from app.market_data.schemas import HistoricalCandle


class IndicatorService:
    """
    Calculates every registered indicator.
    """

    def __init__(
        self,
        registry: IndicatorRegistry | None = None,
    ):
        self._registry = registry or IndicatorRegistry()

    @property
    def registry(self) -> IndicatorRegistry:
        return self._registry

    def calculate_all(
        self,
        candles: Sequence[HistoricalCandle],
    ) -> dict[str, list]:
        """
        Calculate every registered indicator.
        """

        results: dict[str, list] = {}

        for indicator in self.registry.indicators:

            key = self._build_key(indicator)

            results[key] = indicator.calculate(
                list(candles)
            )

        return results

    @staticmethod
    def _build_key(
        indicator,
    ) -> str:

        if hasattr(indicator, "period"):

            return (
                f"{indicator.indicator_type.value}"
                f"_{indicator.period}"
            )

        return indicator.indicator_type.value