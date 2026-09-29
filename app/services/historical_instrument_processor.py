from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.feature_store.mapper import FeatureValueMapper
from app.indicators.service import IndicatorService
from app.market_data.schemas import HistoricalCandle
from app.repositories.feature_value_repository import (
    FeatureValueRepository,
)


class HistoricalInstrumentProcessor:
    """
    Processes one instrument's historical candles
    and stores every calculated feature.
    """

    def __init__(
        self,
        session: Session,
        indicator_service: IndicatorService,
        mapper: FeatureValueMapper,
        repository: FeatureValueRepository,
    ):

        self.session = session
        self.indicator_service = indicator_service
        self.mapper = mapper
        self.repository = repository

    def process(
        self,
        instrument_id: int,
        candles: Sequence[HistoricalCandle],
    ) -> int:
        """
        Calculate indicators and persist them.

        Returns the number of rows written.
        """

        indicator_results = (
            self.indicator_service.calculate_all(
                candles
            )
        )

        rows = self.mapper.map_history(
            instrument_id=instrument_id,
            indicator_results=indicator_results,
        )

        self.repository.bulk_insert(rows)

        self.session.commit()

        return len(rows)