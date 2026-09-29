from collections.abc import Sequence

from app.indicators.service import IndicatorService
from app.indicators.snapshot_builder import SnapshotBuilder
from app.market_data.schemas import HistoricalCandle
from app.scanner.schemas import StockSnapshot


class MarketAnalyzer:
    """
    Coordinates indicator calculation
    and snapshot creation.
    """

    def __init__(self):

        self.service = IndicatorService()

        self.builder = SnapshotBuilder()

    def analyze(
        self,
        candles: Sequence[HistoricalCandle],
    ) -> StockSnapshot:

        indicator_results = self.service.calculate_all(
            candles
        )

        return self.builder.build(
            indicator_results
        )