from decimal import Decimal

from app.indicators.schemas import (
    IndicatorValue,
    MACDValue,
    BollingerBandsValue,
    RawFieldValue,
)
from app.scanner.schemas import (
    IndicatorSnapshot,
    StockSnapshot,
)


class SnapshotBuilder:
    """
    Builds scanner snapshots from
    indicator calculation results.

    Converts indicator objects into a flat
    dictionary that the Scanner Engine can use.
    """

    def build(
        self,
        indicator_results: dict[str, list],
    ) -> StockSnapshot:

        current: dict[str, Decimal] = {}
        previous: dict[str, Decimal] = {}

        for values in indicator_results.values():

            if len(values) < 2:
                continue

            latest = values[-1]
            prev = values[-2]

            # ----------------------------------
            # Standard indicators
            # SMA, EMA, RSI, ATR, ADX, Supertrend
            # ----------------------------------
            if isinstance(latest, IndicatorValue):

                key = (
                    f"{latest.indicator.value}"
                    f"{latest.period}"
                )

                current[key] = latest.value
                previous[key] = prev.value

            # ----------------------------------
            # MACD
            # ----------------------------------
            elif isinstance(latest, MACDValue):

                current["MACD"] = latest.macd
                current["MACD_SIGNAL"] = latest.signal
                current["MACD_HISTOGRAM"] = latest.histogram

                previous["MACD"] = prev.macd
                previous["MACD_SIGNAL"] = prev.signal
                previous["MACD_HISTOGRAM"] = prev.histogram

            # ----------------------------------
            # Bollinger Bands
            # ----------------------------------
            elif isinstance(latest, BollingerBandsValue):

                current["BB_UPPER"] = latest.upper
                current["BB_MIDDLE"] = latest.middle
                current["BB_LOWER"] = latest.lower

                previous["BB_UPPER"] = prev.upper
                previous["BB_MIDDLE"] = prev.middle
                previous["BB_LOWER"] = prev.lower

            # ----------------------------------
            # Raw market fields
            # ----------------------------------
            elif isinstance(latest, RawFieldValue):

                current[latest.field] = latest.value
                previous[latest.field] = prev.value

        return StockSnapshot(
            current=IndicatorSnapshot(
                values=current,
            ),
            previous=IndicatorSnapshot(
                values=previous,
            ),
        )