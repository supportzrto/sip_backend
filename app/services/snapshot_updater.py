from __future__ import annotations

from app.models.feature.snapshot import FeatureSnapshot
from app.models.feature.value import FeatureValue
from app.repositories.snapshot_repository import FeatureSnapshotRepository


class SnapshotUpdater:
    """
    Keeps the feature_snapshot table synchronized
    with newly generated historical features.

    Only the latest value for each feature is stored
    in the snapshot table.
    """

    def __init__(
        self,
        repository: FeatureSnapshotRepository,
    ) -> None:

        self.repository = repository

    def update(
        self,
        feature_values: list[FeatureValue],
    ) -> None:

        if not feature_values:
            return

        #
        # Keep only the latest FeatureValue for each feature
        #
        latest: dict[int, FeatureValue] = {}

        for value in feature_values:

            existing = latest.get(
                value.feature_definition_id
            )

            if (
                existing is None
                or value.trade_date > existing.trade_date
            ):
                latest[value.feature_definition_id] = value

        #
        # Build snapshot rows ONCE
        #
        snapshots = [
            FeatureSnapshot(
                instrument_id=value.instrument_id,
                feature_definition_id=value.feature_definition_id,
                trade_date=value.trade_date,
                decimal_value=value.decimal_value,
                integer_value=value.integer_value,
                boolean_value=value.boolean_value,
            )
            for value in latest.values()
        ]

        print(
            f"Instrument: {feature_values[0].instrument_id} | "
            f"Feature values: {len(feature_values)}"
        )
        print(
            f"Latest snapshots: {len(snapshots)}"
        )

        #
        # Execute ONE UPSERT for the instrument
        #
        self.repository.bulk_upsert(
            snapshots,
        )