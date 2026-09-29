from __future__ import annotations

from collections import defaultdict

from app.repositories.snapshot_repository import (
    FeatureSnapshotRepository,
)
from app.scanner.mappers.snapshot_mapper import SnapshotMapper
from app.scanner.schemas import StockSnapshot


class SnapshotLoader:
    """
    Loads the latest feature snapshots and converts them into
    StockSnapshot objects.
    """

    def __init__(
        self,
        repository: FeatureSnapshotRepository,
        mapper: SnapshotMapper,
    ) -> None:

        self.repository = repository
        self.mapper = mapper

    def load(self) -> dict[str, StockSnapshot]:

        rows = self.repository.get_all()

        grouped = defaultdict(list)

        for row in rows:

            grouped[row.instrument_id].append(row)

        snapshots: dict[str, StockSnapshot] = {}

        for instrument_rows in grouped.values():

            symbol = instrument_rows[0].instrument.symbol

            snapshots[symbol] = self.mapper.map(instrument_rows)

        return snapshots