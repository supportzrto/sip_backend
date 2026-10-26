from __future__ import annotations

import time
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.feature_store.batch_writer import BatchWriter
from app.feature_store.builder import FeatureStoreBuilder
from app.market_data.importer.instrument_importer import InstrumentImporter
from app.market_data.providers.base import HistoricalCandle
from app.market_data.providers.csv_provider import CSVProvider
from app.repositories.feature_value_repository import FeatureValueRepository
from app.repositories.instrument_repository import InstrumentRepository
from app.services.snapshot_updater import SnapshotUpdater

# How far back to look on a repeat run, before the last already-
# processed date. Generous enough to correctly re-seed the longest
# lookback indicators (EMA200/SMA200 etc. need ~200 trading days;
# 500 calendar days is comfortably more than that even accounting
# for weekends/holidays) while still being vastly smaller than a
# full multi-year history for an established instrument.
INCREMENTAL_LOOKBACK_DAYS = 500

# The 500-day window above exists only to SEED the indicators
# correctly. The feature rows it produces for dates the database
# already holds are identical to what's stored, so on a repeat run
# only the last few days before the previous high-water mark are
# written again (to absorb a late correction to the newest days);
# everything older is left alone. Without this, every daily run
# rewrote ~500 days x ~23 features for every instrument to add one
# day's worth of new rows -- over 100x the writes needed, and in
# Postgres every rewrite leaves a dead row version and dead index
# entries behind, which is how a 50 GB volume filled up.
# A force_full_resync still rewrites everything.
INCREMENTAL_REWRITE_DAYS = 7


class HistoricalFeatureProcessor:
    """
    Orchestrates historical feature generation for all instruments.

    Responsibilities:
    - Discover/register instruments from the CSV data
    - Load instruments
    - Load historical candles (full history on first run, only a
      trailing window on repeat runs -- see INCREMENTAL_LOOKBACK_DAYS)
    - Build feature values
    - Persist feature values (upsert, so re-runs are safe)
    - Continue processing on failures
    - Report progress
    """

    def __init__(
        self,
        session: Session,
        instrument_repository: InstrumentRepository,
        feature_value_repository: FeatureValueRepository,
        csv_provider: CSVProvider,
        builder: FeatureStoreBuilder,
        writer: BatchWriter,
        snapshot_updater: SnapshotUpdater,
        instrument_importer: InstrumentImporter | None = None,
    ) -> None:
        self.session = session
        self.instrument_repository = instrument_repository
        self.feature_value_repository = feature_value_repository
        self.csv_provider = csv_provider
        self.builder = builder
        self.writer = writer
        self.snapshot_updater = snapshot_updater

        self.instrument_importer = instrument_importer or InstrumentImporter(
            provider=csv_provider,
            repository=instrument_repository,
        )

    def run(
        self,
        force_full_resync: bool = False,
    ) -> None:

        newly_registered = self.instrument_importer.import_instruments()

        print(f"Newly Registered Instruments : {newly_registered}")

        instruments = self.instrument_repository.get_all()

        latest_trade_dates = (
            {}
            if force_full_resync
            else self.feature_value_repository.get_latest_trade_date_by_instrument()
        )

        print("=" * 70)
        print("Building Historical Feature Store")

        if force_full_resync:
            print("(forced full resync -- ignoring existing progress)")

        print("=" * 70)
        print(f"Instruments Found : {len(instruments)}")
        print()

        total_rows = 0
        processed = 0
        skipped = 0
        failed: list[dict[str, str]] = []

        for index, instrument in enumerate(instruments, start=1):

            try:
                rows_written = self.process_instrument(
                    index=index,
                    total=len(instruments),
                    instrument_id=instrument.id,
                    symbol=instrument.symbol,
                    already_processed_through=latest_trade_dates.get(
                        instrument.id,
                    ),
                )

                if rows_written == -1:
                    skipped += 1
                else:
                    processed += 1
                    total_rows += rows_written

            except Exception as ex:
                self.session.rollback()

                failed.append(
                    {
                        "symbol": instrument.symbol,
                        "error": str(ex),
                    }
                )

                print(f"FAILED : {instrument.symbol}")
                print(ex)
                print("-" * 70)

        self.writer.finish()

        print()
        print("=" * 70)
        print("Build Complete")
        print("=" * 70)
        print(f"Processed Instruments : {processed}")
        print(f"Skipped Instruments   : {skipped}")
        print(f"Failed Instruments    : {len(failed)}")
        print(f"Feature Rows Written  : {total_rows:,}")

        if failed:

            print()
            print("Failure Summary")
            print("-" * 70)

            for item in failed:
                print(f"{item['symbol']} -> {item['error']}")

        print("=" * 70)

    def process_instrument(
        self,
        *,
        index: int,
        total: int,
        instrument_id: int,
        symbol: str,
        already_processed_through: date | None = None,
    ) -> int:

        print("=" * 70)
        print(f"[{index}/{total}] {symbol}")
        print("=" * 70)

        start = time.perf_counter()

        # First run: need the full history to correctly seed every
        # indicator from the start. Repeat run: only fetch a trailing
        # window -- re-reading and recomputing a full multi-year
        # history every day (when in reality only the newest day(s)
        # changed) is the difference between a sync that finishes in
        # seconds vs. one that takes hours at real dataset scale.
        fetch_start_date = None

        if already_processed_through is not None:
            fetch_start_date = already_processed_through - timedelta(
                days=INCREMENTAL_LOOKBACK_DAYS,
            )

        candles: list[HistoricalCandle] = self.csv_provider.fetch_daily_candles(
            symbol,
            start_date=fetch_start_date,
        )

        if not candles:
            print("No historical candles found.")
            print()
            return 0

        latest_candle_date = max(candle.trade_date for candle in candles)

        if (
            already_processed_through is not None
            and latest_candle_date <= already_processed_through
        ):
            print(f"Already up to date (through {already_processed_through}).")
            print("Skipping...")
            print()
            return -1

        feature_rows = self.builder.build(
            instrument_id=instrument_id,
            candles=candles,
        )

        if already_processed_through is not None:
            rewrite_from = already_processed_through - timedelta(
                days=INCREMENTAL_REWRITE_DAYS,
            )
            feature_rows = [
                row for row in feature_rows if row.trade_date >= rewrite_from
            ]

        self.snapshot_updater.update(
            feature_rows,
        )

        self.writer.add(feature_rows)

        elapsed = time.perf_counter() - start

        print(f"Candles      : {len(candles):,}")
        print(f"Feature Rows : {len(feature_rows):,}")
        print(f"Elapsed      : {elapsed:.2f} sec")
        print()

        return len(feature_rows)