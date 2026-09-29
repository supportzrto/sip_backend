from fastapi import Depends
from sqlalchemy.orm import Session
from app.api.dependencies.database import get_db
from app.feature_store.cache import FeatureNameCache
from app.repositories.feature_definition_repository import FeatureDefinitionRepository
from app.repositories.feature_value_repository import FeatureValueRepository
from app.repositories.scan_run_repository import ScanRunRepository
from app.repositories.snapshot_repository import FeatureSnapshotRepository
from app.repositories.instrument_repository import InstrumentRepository
from app.scanner.engine import ScannerEngine
from app.services.backtest_service import BacktestService
from app.services.scanner_service import ScannerService


def get_scanner_service(
    db: Session = Depends(get_db),
) -> ScannerService:

    feature_definition_repository = FeatureDefinitionRepository(db)

    return ScannerService(
        instrument_repository=InstrumentRepository(db),
        feature_snapshot_repository=FeatureSnapshotRepository(db),
        feature_value_repository=FeatureValueRepository(db),
        feature_name_cache=FeatureNameCache(feature_definition_repository),
        scan_run_repository=ScanRunRepository(db),
        engine=ScannerEngine(),
    )


def get_scan_run_repository(
    db: Session = Depends(get_db),
) -> ScanRunRepository:

    return ScanRunRepository(db)


def get_backtest_service(
    db: Session = Depends(get_db),
) -> BacktestService:

    return BacktestService(
        instrument_repository=InstrumentRepository(db),
        feature_value_repository=FeatureValueRepository(db),
    )