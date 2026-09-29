from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.models.instrument import Instrument
from app.models.scan_result import ScanResult as ScanResultModel
from app.repositories.scan_run_repository import ScanRunRepository


def create_session():

    engine = create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)

    return Session()


def create_instrument(session, symbol="RELIANCE"):

    instrument = Instrument(
        symbol=symbol,
        company_name="Reliance Industries",
        exchange="NSE",
        instrument_type="EQ",
        isin="INE002A01018",
        provider="NSE",
        provider_token="12345",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    session.add(instrument)
    session.commit()

    return instrument


def test_create_run_persists_run_and_results():

    session = create_session()
    instrument = create_instrument(session)

    repository = ScanRunRepository(session)

    result = ScanResultModel(
        instrument_id=instrument.id,
        symbol=instrument.symbol,
        reasons=["EMA20 crossed above EMA50 (105.00 vs 100.00)"],
    )

    started_at = datetime(2026, 8, 9, 9, 0, tzinfo=UTC)
    completed_at = datetime(2026, 8, 9, 9, 0, 5, tzinfo=UTC)

    run = repository.create_run(
        strategy="Breakout Test",
        stocks_scanned=1,
        matches_found=1,
        started_at=started_at,
        completed_at=completed_at,
        results=[result],
    )

    assert run.id is not None
    assert run.matches_found == 1


def test_get_recent_runs_orders_by_started_at_desc():

    session = create_session()
    instrument = create_instrument(session)

    repository = ScanRunRepository(session)

    repository.create_run(
        strategy="Run A",
        stocks_scanned=1,
        matches_found=0,
        started_at=datetime(2026, 8, 8, tzinfo=UTC),
        completed_at=datetime(2026, 8, 8, 0, 0, 5, tzinfo=UTC),
        results=[],
    )

    repository.create_run(
        strategy="Run B",
        stocks_scanned=1,
        matches_found=0,
        started_at=datetime(2026, 8, 9, tzinfo=UTC),
        completed_at=datetime(2026, 8, 9, 0, 0, 5, tzinfo=UTC),
        results=[],
    )

    runs = repository.get_recent_runs()

    assert [run.strategy for run in runs] == ["Run B", "Run A"]


def test_get_run_with_results_includes_reasons():

    session = create_session()
    instrument = create_instrument(session)

    repository = ScanRunRepository(session)

    result = ScanResultModel(
        instrument_id=instrument.id,
        symbol=instrument.symbol,
        reasons=["RSI14 (28.00) < 35.00"],
    )

    run = repository.create_run(
        strategy="Swing Strategy",
        stocks_scanned=1,
        matches_found=1,
        started_at=datetime(2026, 8, 9, tzinfo=UTC),
        completed_at=datetime(2026, 8, 9, 0, 0, 5, tzinfo=UTC),
        results=[result],
    )

    fetched = repository.get_run_with_results(run.id)

    assert fetched is not None
    assert len(fetched.results) == 1
    assert fetched.results[0].symbol == "RELIANCE"
    assert fetched.results[0].reasons == ["RSI14 (28.00) < 35.00"]


def test_get_run_with_results_returns_none_when_missing():

    session = create_session()

    repository = ScanRunRepository(session)

    assert repository.get_run_with_results(999) is None


def test_get_recent_runs_supports_pagination():

    session = create_session()
    instrument = create_instrument(session)

    repository = ScanRunRepository(session)

    for day in range(1, 6):
        repository.create_run(
            strategy=f"Run {day}",
            stocks_scanned=1,
            matches_found=0,
            started_at=datetime(2026, 8, day, tzinfo=UTC),
            completed_at=datetime(2026, 8, day, 0, 0, 5, tzinfo=UTC),
            results=[],
        )

    page_one = repository.get_recent_runs(limit=2, offset=0)
    page_two = repository.get_recent_runs(limit=2, offset=2)

    assert [run.strategy for run in page_one] == ["Run 5", "Run 4"]
    assert [run.strategy for run in page_two] == ["Run 3", "Run 2"]

    assert repository.count_runs() == 5


def test_get_recent_runs_filters_by_strategy():

    session = create_session()
    instrument = create_instrument(session)

    repository = ScanRunRepository(session)

    repository.create_run(
        strategy="Breakout Scan",
        stocks_scanned=1,
        matches_found=0,
        started_at=datetime(2026, 8, 8, tzinfo=UTC),
        completed_at=datetime(2026, 8, 8, 0, 0, 5, tzinfo=UTC),
        results=[],
    )

    repository.create_run(
        strategy="Swing Strategy",
        stocks_scanned=1,
        matches_found=0,
        started_at=datetime(2026, 8, 9, tzinfo=UTC),
        completed_at=datetime(2026, 8, 9, 0, 0, 5, tzinfo=UTC),
        results=[],
    )

    runs = repository.get_recent_runs(strategy="Swing Strategy")

    assert [run.strategy for run in runs] == ["Swing Strategy"]
    assert repository.count_runs(strategy="Swing Strategy") == 1


def test_get_recent_runs_filters_by_symbol():

    session = create_session()
    instrument = create_instrument(session, symbol="RELIANCE")
    other_instrument = create_instrument(session, symbol="TCS")

    repository = ScanRunRepository(session)

    repository.create_run(
        strategy="Run A",
        stocks_scanned=2,
        matches_found=1,
        started_at=datetime(2026, 8, 8, tzinfo=UTC),
        completed_at=datetime(2026, 8, 8, 0, 0, 5, tzinfo=UTC),
        results=[
            ScanResultModel(
                instrument_id=instrument.id,
                symbol="RELIANCE",
                reasons=["RSI14 (25.00) < 30.00"],
            )
        ],
    )

    repository.create_run(
        strategy="Run B",
        stocks_scanned=2,
        matches_found=1,
        started_at=datetime(2026, 8, 9, tzinfo=UTC),
        completed_at=datetime(2026, 8, 9, 0, 0, 5, tzinfo=UTC),
        results=[
            ScanResultModel(
                instrument_id=other_instrument.id,
                symbol="TCS",
                reasons=["RSI14 (25.00) < 30.00"],
            )
        ],
    )

    runs = repository.get_recent_runs(symbol="RELIANCE")

    assert [run.strategy for run in runs] == ["Run A"]
    assert repository.count_runs(symbol="RELIANCE") == 1


def test_get_recent_runs_filters_by_date_range():

    session = create_session()
    instrument = create_instrument(session)

    repository = ScanRunRepository(session)

    repository.create_run(
        strategy="Early Run",
        stocks_scanned=1,
        matches_found=0,
        started_at=datetime(2026, 8, 1, tzinfo=UTC),
        completed_at=datetime(2026, 8, 1, 0, 0, 5, tzinfo=UTC),
        results=[],
    )

    repository.create_run(
        strategy="Late Run",
        stocks_scanned=1,
        matches_found=0,
        started_at=datetime(2026, 8, 9, tzinfo=UTC),
        completed_at=datetime(2026, 8, 9, 0, 0, 5, tzinfo=UTC),
        results=[],
    )

    runs = repository.get_recent_runs(
        started_after=datetime(2026, 8, 5, tzinfo=UTC),
    )

    assert [run.strategy for run in runs] == ["Late Run"]