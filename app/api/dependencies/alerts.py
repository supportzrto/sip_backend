from fastapi import Depends
from sqlalchemy.orm import Session

from app.api.dependencies.database import get_db
from app.auth.repository import UserRepository
from app.feature_store.cache import FeatureNameCache
from app.repositories.alert_rule_repository import AlertRuleRepository
from app.repositories.feature_definition_repository import (
    FeatureDefinitionRepository,
)
from app.repositories.feature_value_repository import (
    FeatureValueRepository,
)
from app.repositories.instrument_repository import InstrumentRepository
from app.repositories.saved_strategy_repository import (
    SavedStrategyRepository,
)
from app.repositories.scan_run_repository import ScanRunRepository
from app.repositories.snapshot_repository import (
    FeatureSnapshotRepository,
)
from app.repositories.watchlist_repository import WatchlistRepository
from app.scanner.engine import ScannerEngine
from app.services.alert_service import AlertService
from app.services.scanner_service import ScannerService


def get_alert_rule_repository(
    db: Session = Depends(get_db),
) -> AlertRuleRepository:

    return AlertRuleRepository(db)


def get_alert_service(
    db: Session = Depends(get_db),
) -> AlertService:

    feature_definition_repository = FeatureDefinitionRepository(db)

    scanner_service = ScannerService(
        instrument_repository=InstrumentRepository(db),
        feature_snapshot_repository=FeatureSnapshotRepository(db),
        feature_value_repository=FeatureValueRepository(db),
        feature_name_cache=FeatureNameCache(
            feature_definition_repository,
        ),
        scan_run_repository=ScanRunRepository(db),
        engine=ScannerEngine(),
    )

    return AlertService(
        scanner_service=scanner_service,
        alert_rule_repository=AlertRuleRepository(db),
        watchlist_repository=WatchlistRepository(db),
        instrument_repository=InstrumentRepository(db),
        saved_strategy_repository=SavedStrategyRepository(db),
        user_repository=UserRepository(db),
    )