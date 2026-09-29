from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from app.feature_store.cache import FeatureNameCache
from app.models.feature.snapshot import FeatureSnapshot
from app.models.feature.value import FeatureValue
from app.models.instrument import Instrument
from app.models.scan_result import ScanResult as ScanResultModel
from app.repositories.feature_value_repository import (
    FeatureValueRepository,
)
from app.repositories.scan_run_repository import ScanRunRepository
from app.repositories.snapshot_repository import (
    FeatureSnapshotRepository,
)
from app.repositories.instrument_repository import (
    InstrumentRepository,
)
from app.scanner.engine import ScannerEngine
from app.scanner.enums import IndicatorField
from app.scanner.schemas import (
    IndicatorSnapshot,
    ScanRequest,
    ScanResult,
    StockSnapshot,
)


class ScannerService:
    """
    Orchestrates loading scanner data from the database,
    evaluating scan requests, and persisting the results.
    """

    def __init__(
        self,
        instrument_repository: InstrumentRepository,
        feature_snapshot_repository: FeatureSnapshotRepository,
        feature_value_repository: FeatureValueRepository,
        feature_name_cache: FeatureNameCache,
        scan_run_repository: ScanRunRepository,
        engine: ScannerEngine,
    ) -> None:

        self._instrument_repository = instrument_repository
        self._feature_snapshot_repository = feature_snapshot_repository
        self._feature_value_repository = feature_value_repository
        self._feature_name_cache = feature_name_cache
        self._scan_run_repository = scan_run_repository
        self._engine = engine

    def scan(
        self,
        request: ScanRequest,
        user_id: int | None = None,
        symbols: list[str] | None = None,
    ) -> list[ScanResult]:

        started_at = datetime.now(timezone.utc)

        instruments = self._instrument_repository.get_all()

        if symbols is not None:
            allowed = {symbol.upper() for symbol in symbols}
            instruments = [
                instrument
                for instrument in instruments
                if instrument.symbol.upper() in allowed
            ]

        snapshots = self._feature_snapshot_repository.get_all()

        previous_values = (
            self._feature_value_repository.get_previous_feature_values()
        )

        stocks, instrument_by_symbol = self._build_stock_snapshots(
            instruments=instruments,
            snapshots=snapshots,
            previous_values=previous_values,
        )

        results = self._engine.scan(
            stocks=stocks,
            request=request,
        )

        completed_at = datetime.now(timezone.utc)

        self._persist_run(
            request=request,
            results=results,
            stocks_scanned=len(stocks),
            instrument_by_symbol=instrument_by_symbol,
            started_at=started_at,
            completed_at=completed_at,
            user_id=user_id,
        )

        return results

    def _persist_run(
        self,
        request: ScanRequest,
        results: list[ScanResult],
        stocks_scanned: int,
        instrument_by_symbol: dict[str, Instrument],
        started_at: datetime,
        completed_at: datetime,
        user_id: int | None = None,
    ) -> None:
        """
        Save the scan run and its matched results to the database.

        A result is skipped only if its instrument can't be resolved
        (shouldn't normally happen, since results come from the same
        instrument set that was scanned) — the run itself is still
        recorded either way.
        """

        result_rows = []

        for result in results:

            instrument = instrument_by_symbol.get(result.symbol)

            if instrument is None:
                continue

            result_rows.append(
                ScanResultModel(
                    instrument_id=instrument.id,
                    symbol=result.symbol,
                    reasons=result.reasons,
                )
            )

        self._scan_run_repository.create_run(
            strategy=request.strategy_name,
            stocks_scanned=stocks_scanned,
            matches_found=len(results),
            started_at=started_at,
            completed_at=completed_at,
            results=result_rows,
            user_id=user_id,
        )

    def _build_stock_snapshots(
        self,
        instruments: list[Instrument],
        snapshots: list[FeatureSnapshot],
        previous_values: list[FeatureValue],
    ) -> tuple[dict[str, StockSnapshot], dict[str, Instrument]]:

        instrument_lookup = {
            instrument.id: instrument
            for instrument in instruments
        }

        current_lookup: dict[
            int,
            dict[IndicatorField, Decimal],
        ] = {}

        for snapshot in snapshots:

            value = self._extract_value(snapshot)

            if value is None:
                continue

            field = self._feature_name_cache.get_name(
                snapshot.feature_definition_id,
            )

            current_lookup.setdefault(
                snapshot.instrument_id,
                {},
            )[field] = Decimal(value)

        previous_lookup: dict[
            int,
            dict[IndicatorField, Decimal],
        ] = {}

        for feature_value in previous_values:

            value = self._extract_value(feature_value)

            if value is None:
                continue

            field = self._feature_name_cache.get_name(
                feature_value.feature_definition_id,
            )

            previous_lookup.setdefault(
                feature_value.instrument_id,
                {},
            )[field] = Decimal(value)

        stocks: dict[str, StockSnapshot] = {}
        instrument_by_symbol: dict[str, Instrument] = {}

        for instrument_id, indicators in current_lookup.items():

            instrument = instrument_lookup.get(
                instrument_id,
            )

            if instrument is None:
                continue

            stocks[instrument.symbol] = StockSnapshot(
                current=IndicatorSnapshot(
                    values=indicators,
                ),
                previous=IndicatorSnapshot(
                    values=previous_lookup.get(
                        instrument_id,
                        {},
                    ),
                ),
            )

            instrument_by_symbol[instrument.symbol] = instrument

        return stocks, instrument_by_symbol

    @staticmethod
    def _extract_value(
        snapshot: FeatureSnapshot | FeatureValue,
    ) -> Decimal | None:

        if snapshot.decimal_value is not None:
            return snapshot.decimal_value

        if snapshot.integer_value is not None:
            return Decimal(snapshot.integer_value)

        return None