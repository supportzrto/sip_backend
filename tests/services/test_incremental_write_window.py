"""
A repeat (incremental) sync used to compute ~500 days of features per
instrument and then write ALL of them back, to add one day's worth of
new rows -- over 100x the writes needed. In Postgres every rewrite
leaves a dead row version plus dead index entries behind, which is
how a 50 GB volume filled up.

The trailing window is still computed (indicators need it to seed
correctly), but only the last INCREMENTAL_REWRITE_DAYS before the
previous high-water mark, plus anything newer, is written. These
tests pin that behaviour down, including its one deliberate
trade-off: a correction to an OLD candle is not picked up by an
incremental run (that needs force_full_resync).
"""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.feature_store.batch_writer import BatchWriter
from app.feature_store.builder import FeatureStoreBuilder
from app.feature_store.cache import FeatureIdCache
from app.feature_store.mapper import FeatureValueMapper
from app.indicators.service import IndicatorService
from app.market_data.providers.base import MarketDataProvider
from app.market_data.schemas import HistoricalCandle, HistoricalInstrument
from app.models.feature.definition import FeatureDefinition
from app.models.feature.snapshot import FeatureSnapshot
from app.models.feature.value import FeatureValue
from app.repositories.feature_definition_repository import (
    FeatureDefinitionRepository,
)
from app.repositories.feature_value_repository import FeatureValueRepository
from app.repositories.instrument_repository import InstrumentRepository
from app.repositories.snapshot_repository import FeatureSnapshotRepository
from app.services.historical_feature_processor import (
    INCREMENTAL_REWRITE_DAYS,
    HistoricalFeatureProcessor,
)
from app.services.snapshot_updater import SnapshotUpdater

FIRST_DAY = date(2026, 1, 1)


class GrowingProvider(MarketDataProvider):
    """
    In-memory provider whose history can grow between runs (like new
    trading days arriving) and whose individual closes can be
    overridden (like a corrected candle).
    """

    def __init__(self, symbols: list[str], days: int):
        self._symbols = symbols
        self.days = days
        self.close_overrides: dict[date, Decimal] = {}

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

        candles = [
            HistoricalCandle(
                symbol=symbol,
                trade_date=FIRST_DAY + timedelta(days=day),
                open=Decimal("100"),
                high=Decimal("105"),
                low=Decimal("99"),
                close=self.close_overrides.get(
                    FIRST_DAY + timedelta(days=day), Decimal("102"),
                ),
                volume=1000,
            )
            for day in range(self.days)
        ]

        if start_date is not None:
            candles = [c for c in candles if c.trade_date >= start_date]

        return candles


def build_processor(session, provider) -> HistoricalFeatureProcessor:

    from app.services.feature_sync_service import FeatureSyncService

    FeatureSyncService(session=session).sync()

    feature_value_repository = FeatureValueRepository(session)

    mapper = FeatureValueMapper(
        FeatureIdCache(FeatureDefinitionRepository(session)),
    )

    return HistoricalFeatureProcessor(
        session=session,
        instrument_repository=InstrumentRepository(session),
        feature_value_repository=feature_value_repository,
        csv_provider=provider,
        builder=FeatureStoreBuilder(
            indicator_service=IndicatorService(),
            mapper=mapper,
        ),
        writer=BatchWriter(
            session=session,
            repository=feature_value_repository,
        ),
        snapshot_updater=SnapshotUpdater(
            repository=FeatureSnapshotRepository(session),
        ),
    )


def make_session():

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def record_writes(processor) -> list[list[FeatureValue]]:
    """Wraps the writer so each batch of rows handed to it is kept."""

    batches: list[list[FeatureValue]] = []
    original_add = processor.writer.add

    def spy(rows):
        rows = list(rows)
        batches.append(rows)
        return original_add(rows)

    processor.writer.add = spy
    return batches


def stored_close(session, day: date) -> Decimal:

    definition_id = session.scalar(
        select(FeatureDefinition.id).where(FeatureDefinition.name == "CLOSE"),
    )

    return session.scalar(
        select(FeatureValue.decimal_value).where(
            FeatureValue.feature_definition_id == definition_id,
            FeatureValue.trade_date == day,
        ),
    )


def test_repeat_run_writes_only_the_recent_window():

    session = make_session()
    provider = GrowingProvider(["RELIANCE"], days=60)
    processor = build_processor(session, provider)

    processor.run()  # first run: nothing stored yet, writes everything

    last_stored_day = FIRST_DAY + timedelta(days=59)

    writes = record_writes(processor)
    provider.days = 63  # three new trading days arrive
    processor.run()

    written_days = {row.trade_date for batch in writes for row in batch}

    assert min(written_days) == last_stored_day - timedelta(
        days=INCREMENTAL_REWRITE_DAYS,
    )
    assert max(written_days) == last_stored_day + timedelta(days=3)

    # Nothing was lost by writing less: every day is stored, once.
    stored_days = session.scalar(
        select(func.count(func.distinct(FeatureValue.trade_date))),
    )
    assert stored_days == 63


def test_far_fewer_rows_are_written_than_on_the_first_run():

    session = make_session()
    provider = GrowingProvider(["RELIANCE"], days=60)
    processor = build_processor(session, provider)

    first = record_writes(processor)
    processor.run()
    first_rows = sum(len(batch) for batch in first)

    second = record_writes(processor)
    provider.days = 63
    processor.run()
    second_rows = sum(len(batch) for batch in second)

    assert second_rows < first_rows / 3


def test_force_full_resync_still_rewrites_everything():

    session = make_session()
    provider = GrowingProvider(["RELIANCE"], days=60)
    processor = build_processor(session, provider)

    processor.run()

    writes = record_writes(processor)
    processor.run(force_full_resync=True)

    written_days = {row.trade_date for batch in writes for row in batch}

    assert min(written_days) == FIRST_DAY
    assert max(written_days) == FIRST_DAY + timedelta(days=59)


def test_snapshot_still_tracks_the_newest_day():

    session = make_session()
    provider = GrowingProvider(["RELIANCE"], days=60)
    processor = build_processor(session, provider)

    processor.run()

    provider.days = 63
    processor.run()

    newest = session.scalar(select(func.max(FeatureSnapshot.trade_date)))

    assert newest == FIRST_DAY + timedelta(days=62)


def test_a_late_correction_to_a_recent_day_is_applied_with_the_next_new_day():
    """
    Note an instrument whose CSV has no new dates at all is skipped
    outright ("Already up to date") -- that was already the case. In
    the daily flow a new day arrives every time, and a correction to
    one of the last few days travels with it.
    """

    session = make_session()
    provider = GrowingProvider(["RELIANCE"], days=60)
    processor = build_processor(session, provider)

    processor.run()

    recent_day = FIRST_DAY + timedelta(days=57)  # inside the rewrite window
    assert stored_close(session, recent_day) == Decimal("102")

    provider.close_overrides[recent_day] = Decimal("200")
    provider.days = 61  # a new day arrives, so the instrument is processed
    processor.run()

    assert stored_close(session, recent_day) == Decimal("200")


def test_a_correction_to_an_old_candle_needs_a_full_resync():
    """
    The deliberate trade-off. An incremental run no longer rewrites
    history, so a corrected OLD candle is not picked up until
    force_full_resync -- which is also what you'd run after adjusting
    a stock's history for a split.
    """

    session = make_session()
    provider = GrowingProvider(["RELIANCE"], days=60)
    processor = build_processor(session, provider)

    processor.run()

    old_day = FIRST_DAY + timedelta(days=10)  # far outside the window
    provider.close_overrides[old_day] = Decimal("300")
    provider.days = 61  # the instrument IS processed -- the window is what excludes old_day

    processor.run()
    assert stored_close(session, old_day) == Decimal("102")  # not picked up

    processor.run(force_full_resync=True)
    assert stored_close(session, old_day) == Decimal("300")  # now it is