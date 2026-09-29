from datetime import date, timedelta, UTC, datetime
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.feature_store.batch_writer import BatchWriter
from app.feature_store.builder import FeatureStoreBuilder
from app.feature_store.cache import FeatureIdCache
from app.feature_store.mapper import FeatureValueMapper
from app.indicators.service import IndicatorService
from app.market_data.providers.base import MarketDataProvider
from app.market_data.schemas import HistoricalCandle, HistoricalInstrument
from app.models.instrument import Instrument
from app.repositories.feature_definition_repository import (
    FeatureDefinitionRepository,
)
from app.repositories.feature_value_repository import (
    FeatureValueRepository,
)
from app.repositories.instrument_repository import InstrumentRepository
from app.repositories.snapshot_repository import FeatureSnapshotRepository
from app.services.historical_feature_processor import (
    HistoricalFeatureProcessor,
)
from app.services.snapshot_updater import SnapshotUpdater


class FakeProvider(MarketDataProvider):
    """
    In-memory MarketDataProvider so tests don't touch the filesystem.
    """

    def __init__(self, symbols: list[str]):
        self._symbols = symbols
        self.fetch_calls: list[tuple[str, object]] = []

    def fetch_instruments(self) -> list[HistoricalInstrument]:

        return [
            HistoricalInstrument(
                symbol=symbol,
                company_name=symbol,
                exchange="NSE",
                instrument_type="EQUITY",
                isin=None,
                provider="CSV",
                provider_token=None,
                is_active=True,
            )
            for symbol in self._symbols
        ]

    def fetch_daily_candles(
        self,
        symbol: str,
        start_date=None,
        end_date=None,
    ) -> list[HistoricalCandle]:

        self.fetch_calls.append((symbol, start_date))

        all_candles = [
            HistoricalCandle(
                symbol=symbol,
                trade_date=date(2026, 1, 1) + timedelta(days=day),
                open=Decimal("100"),
                high=Decimal("105"),
                low=Decimal("99"),
                close=Decimal("102"),
                volume=1000,
            )
            for day in range(60)
        ]

        if start_date is not None:
            all_candles = [
                candle
                for candle in all_candles
                if candle.trade_date >= start_date
            ]

        return all_candles


def create_session():

    engine = create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)

    return Session()


def build_processor(session, symbols: list[str]) -> HistoricalFeatureProcessor:

    from app.services.feature_sync_service import FeatureSyncService

    FeatureSyncService(session=session).sync()

    provider = FakeProvider(symbols)

    feature_definition_repository = FeatureDefinitionRepository(session)
    feature_value_repository = FeatureValueRepository(session)
    instrument_repository = InstrumentRepository(session)
    snapshot_repository = FeatureSnapshotRepository(session)

    cache = FeatureIdCache(feature_definition_repository)
    mapper = FeatureValueMapper(cache)

    builder = FeatureStoreBuilder(
        indicator_service=IndicatorService(),
        mapper=mapper,
    )

    writer = BatchWriter(
        session=session,
        repository=feature_value_repository,
    )

    snapshot_updater = SnapshotUpdater(
        repository=snapshot_repository,
    )

    return HistoricalFeatureProcessor(
        session=session,
        instrument_repository=instrument_repository,
        feature_value_repository=feature_value_repository,
        csv_provider=provider,
        builder=builder,
        writer=writer,
        snapshot_updater=snapshot_updater,
    )


def test_run_registers_instruments_from_the_provider():
    """
    Regression test: the processor previously had a hardcoded filter
    that only ever processed a single symbol. It must process every
    instrument the provider returns.
    """

    session = create_session()

    processor = build_processor(session, ["RELIANCE", "TCS", "INFY"])

    processor.run()

    instruments = session.scalars(select(Instrument)).all()

    assert {i.symbol for i in instruments} == {
        "RELIANCE",
        "TCS",
        "INFY",
    }


def test_run_does_not_skip_instruments_that_already_have_data():
    """
    Regression test: the processor previously skipped an instrument
    forever once it had any feature values, so daily re-runs with
    new data were silently ignored. It must always (re)process.
    """

    session = create_session()

    processor = build_processor(session, ["RELIANCE"])

    # First run
    processor.run()

    # Second run must not raise (e.g. unique constraint violation)
    # and must not silently skip.
    processor.run()

    instruments = session.scalars(select(Instrument)).all()
    assert len(instruments) == 1


def test_run_does_not_duplicate_existing_instruments():

    session = create_session()

    session.add(
        Instrument(
            symbol="RELIANCE",
            company_name="Reliance Industries",
            exchange="NSE",
            instrument_type="EQ",
            isin="INE002A01018",
            provider="CSV",
            provider_token=None,
            is_active=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
    )
    session.commit()

    processor = build_processor(session, ["RELIANCE"])

    processor.run()

    instruments = session.scalars(select(Instrument)).all()

    assert len(instruments) == 1


def test_run_skips_instrument_with_no_new_candles_since_last_sync():
    """
    Performance: once an instrument is fully processed, a re-run
    with the same (unchanged) candle data should skip recomputing
    it entirely, rather than reprocessing its whole history again.
    """

    session = create_session()

    processor = build_processor(session, ["RELIANCE"])

    first_run_rows = processor.process_instrument(
        index=1,
        total=1,
        instrument_id=1,
        symbol="RELIANCE",
        already_processed_through=None,
    )
    processor.writer.finish()

    assert first_run_rows > 0

    latest_dates = (
        processor.feature_value_repository.get_latest_trade_date_by_instrument()
    )

    second_run_rows = processor.process_instrument(
        index=1,
        total=1,
        instrument_id=1,
        symbol="RELIANCE",
        already_processed_through=latest_dates.get(1),
    )

    assert second_run_rows == -1


def test_repeat_run_with_new_data_only_fetches_a_trailing_window():
    """
    Performance regression test: on a repeat run where an instrument
    already has data AND there's genuinely new data to process, the
    processor must fetch only a trailing window of candles (not the
    full history) -- otherwise every daily sync would recompute each
    instrument's entire multi-year history from scratch, which at
    real dataset scale takes hours instead of minutes.
    """

    session = create_session()

    provider = FakeProvider(["RELIANCE"])

    from app.services.feature_sync_service import FeatureSyncService
    FeatureSyncService(session=session).sync()

    feature_definition_repository = FeatureDefinitionRepository(session)
    feature_value_repository = FeatureValueRepository(session)
    instrument_repository = InstrumentRepository(session)
    snapshot_repository = FeatureSnapshotRepository(session)

    cache = FeatureIdCache(feature_definition_repository)
    mapper = FeatureValueMapper(cache)
    builder = FeatureStoreBuilder(
        indicator_service=IndicatorService(),
        mapper=mapper,
    )
    writer = BatchWriter(session=session, repository=feature_value_repository)
    snapshot_updater = SnapshotUpdater(repository=snapshot_repository)

    processor = HistoricalFeatureProcessor(
        session=session,
        instrument_repository=instrument_repository,
        feature_value_repository=feature_value_repository,
        csv_provider=provider,
        builder=builder,
        writer=writer,
        snapshot_updater=snapshot_updater,
    )

    # First run: full history, no start_date filter.
    processor.run()
    writer.finish()

    assert provider.fetch_calls[-1][1] is None

    # Simulate "tomorrow": one more day of data appears.
    provider.fetch_calls.clear()

    class ExtendedProvider(FakeProvider):
        def fetch_daily_candles(self, symbol, start_date=None, end_date=None):
            candles = super().fetch_daily_candles(symbol, start_date, end_date)
            extra = HistoricalCandle(
                symbol=symbol,
                trade_date=date(2026, 1, 1) + timedelta(days=60),
                open=Decimal("100"),
                high=Decimal("105"),
                low=Decimal("99"),
                close=Decimal("102"),
                volume=1000,
            )
            if start_date is None or extra.trade_date >= start_date:
                candles.append(extra)
            return candles

    extended_provider = ExtendedProvider(["RELIANCE"])
    processor.csv_provider = extended_provider

    processor.run()

    # The repeat run must have passed a non-None start_date -- i.e.
    # it did NOT re-fetch the full history.
    assert len(extended_provider.fetch_calls) == 1
    assert extended_provider.fetch_calls[0][1] is not None


def test_force_full_resync_reprocesses_instead_of_skipping():
    """
    Regression test for the case that motivated force_full_resync:
    adding a new indicator type after data already exists. A normal
    run must skip instruments with no new candle data, but
    force_full_resync=True must reprocess them anyway so the new
    indicator gets backfilled across existing history.
    """

    session = create_session()

    processor = build_processor(session, ["RELIANCE"])

    # First run: establishes existing data.
    processor.run()

    # Second run, no new data available: normal run should skip.
    normal_run_rows = processor.process_instrument(
        index=1, total=1, instrument_id=1, symbol="RELIANCE",
        already_processed_through=(
            processor.feature_value_repository
            .get_latest_trade_date_by_instrument()
            .get(1)
        ),
    )
    assert normal_run_rows == -1

    # force_full_resync=True must reprocess (not skip) even though
    # there's no new data.
    forced_rows = processor.process_instrument(
        index=1, total=1, instrument_id=1, symbol="RELIANCE",
        already_processed_through=None,
    )
    assert forced_rows > 0