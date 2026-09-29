from app.services.snapshot_updater import SnapshotUpdater
from app.repositories.feature_value_repository import (
    FeatureValueRepository,
)


class SnapshotRebuildService:

    def __init__(
        self,
        feature_value_repository: FeatureValueRepository,
        snapshot_updater: SnapshotUpdater,
    ):
        self._feature_value_repository = feature_value_repository
        self._snapshot_updater = snapshot_updater

    def rebuild(self) -> None:

        feature_values = (
            self._feature_value_repository.get_latest_feature_values()
        )

        print(f"Latest feature values: {len(feature_values)}")

        self._snapshot_updater.update(feature_values)