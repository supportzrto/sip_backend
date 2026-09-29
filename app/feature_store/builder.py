from collections.abc import Sequence

from app.feature_store.mapper import FeatureValueMapper
from app.indicators.service import IndicatorService
from app.market_data.schemas import HistoricalCandle
from app.models.feature.value import FeatureValue


class FeatureStoreBuilder:
    """
    Converts historical candles into
    FeatureValue ORM objects.

    No database writes.
    """

    def __init__(
        self,
        indicator_service: IndicatorService,
        mapper: FeatureValueMapper,
    ):
        self.indicator_service = indicator_service
        self.mapper = mapper

    def build(
        self,
        instrument_id: int,
        candles: Sequence[HistoricalCandle],
    ) -> list[FeatureValue]:

        print(f"\n{'=' * 60}")
        print(f"Instrument ID: {instrument_id}")
        print(f"Candles received: {len(candles)}")

        indicator_results = self.indicator_service.calculate_all(
            candles
        )

        print("\nIndicator Results:")
        print("-" * 60)
        for name, values in indicator_results.items():
            print(f"{name:<30} {len(values)}")

        rows = self.mapper.map_history(
            instrument_id=instrument_id,
            indicator_results=indicator_results,
        )

        print(f"\nMapped FeatureValue rows: {len(rows)}")
        print(f"{'=' * 60}\n")

        return rows