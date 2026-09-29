from sqlalchemy.orm import Session

from app.feature_store.batch_writer import BatchWriter
from app.feature_store.builder import FeatureStoreBuilder
from app.feature_store.cache import FeatureIdCache
from app.feature_store.mapper import FeatureValueMapper
from app.indicators.service import IndicatorService
from app.market_data.providers.csv_provider import CSVProvider
from app.repositories.feature_definition_repository import (
    FeatureDefinitionRepository,
)
from app.repositories.feature_value_repository import (
    FeatureValueRepository,
)
from app.repositories.instrument_repository import (
    InstrumentRepository,
)
from app.repositories.snapshot_repository import (
    FeatureSnapshotRepository,
)
from app.services.feature_sync_service import FeatureSyncService
from app.services.historical_feature_processor import (
    HistoricalFeatureProcessor,
)
from app.services.snapshot_updater import SnapshotUpdater


class MarketDataSyncService:
    """
    Runs the full daily pipeline:

    1. Make sure feature definitions exist (idempotent).
    2. Discover/register any new instruments from the CSV data.
    3. Rebuild each instrument's indicators/features from its CSV
       and upsert them into the feature store.
    4. Update the "latest" feature snapshot used by the scanner.

    This is the single entrypoint used by both the CLI command
    (app/commands/build_feature_store.py) and the
    POST /market-data/sync API endpoint, so both stay in sync.
    """

    def __init__(
        self,
        session: Session,
        data_directory: str,
    ) -> None:

        self.session = session
        self.data_directory = data_directory

    def sync(
        self,
        force_full_resync: bool = False,
    ) -> None:

        FeatureSyncService(
            session=self.session,
        ).sync()

        feature_definition_repository = FeatureDefinitionRepository(
            self.session,
        )

        feature_value_repository = FeatureValueRepository(
            self.session,
        )

        instrument_repository = InstrumentRepository(
            self.session,
        )

        snapshot_repository = FeatureSnapshotRepository(
            self.session,
        )

        csv_provider = CSVProvider(
            data_directory=self.data_directory,
        )

        cache = FeatureIdCache(feature_definition_repository)

        mapper = FeatureValueMapper(cache)

        builder = FeatureStoreBuilder(
            indicator_service=IndicatorService(),
            mapper=mapper,
        )

        writer = BatchWriter(
            session=self.session,
            repository=feature_value_repository,
        )

        snapshot_updater = SnapshotUpdater(
            repository=snapshot_repository,
        )

        processor = HistoricalFeatureProcessor(
            session=self.session,
            instrument_repository=instrument_repository,
            feature_value_repository=feature_value_repository,
            csv_provider=csv_provider,
            builder=builder,
            writer=writer,
            snapshot_updater=snapshot_updater,
        )

        processor.run(force_full_resync=force_full_resync)