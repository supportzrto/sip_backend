from sqlalchemy.orm import Session

from app.feature_store.mapper import FeatureValueMapper
from app.repositories.feature_value_repository import (
    FeatureValueRepository,
)


class HistoricalFeatureWriter:
    """
    Writes historical feature values
    for one instrument.
    """

    def __init__(
        self,
        session: Session,
        mapper: FeatureValueMapper,
    ):

        self.repository = FeatureValueRepository(
            session
        )

        self.mapper = mapper

        self.session = session

    def write(
        self,
        instrument_id: int,
        trade_date,
        feature_values,
    ) -> None:
        """
        Persist one day's feature values.
        """

        values = self.mapper.map(

            instrument_id=instrument_id,

            trade_date=trade_date,

            values=feature_values,

        )

        self.repository.bulk_insert(values)

        self.session.commit()