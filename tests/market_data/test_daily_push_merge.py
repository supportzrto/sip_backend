"""
scripts/daily_update.py keeps the deployed backend's copy of the
candle files current by POSTing only the header and the newest few
rows of each file to /market-data/upload, and relying on the endpoint
to merge them into the file already on the backend's volume.

These tests exercise exactly that, with realistic headers (the real
files start with an unnamed index column, ',datetime,symbol,...' or
'.,datetime,symbol,...') in both date styles found in
data/candles/, and then run the real CSVProvider over the merged
file -- the thing the sync actually reads.
"""

import csv
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.constants import UserRole
from app.database.base import Base
import app.models  # noqa: F401  (registers all models on Base)
from app.market_data.providers.csv_provider import CSVProvider
from app.models.user import User

ISO_HEADER = ",datetime,symbol,open,high,low,close,volume,change (%),last day change (%)"
DAYFIRST_HEADER = ".,datetime,symbol,open,high,low,close,volume,change (%),last day change (%)"


@pytest.fixture
def client(tmp_path, monkeypatch):

    data_directory = tmp_path / "candles"
    data_directory.mkdir()

    from app.config.settings import settings as app_settings

    monkeypatch.setattr(app_settings, "DATA_DIRECTORY", str(data_directory))

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSessionLocal = sessionmaker(bind=engine)

    from main import app
    from app.api.dependencies.database import get_db as api_get_db
    import app.database.session as db_session_module

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[api_get_db] = override_get_db
    app.dependency_overrides[db_session_module.get_db] = override_get_db

    with TestClient(app) as test_client:
        test_client.data_directory = data_directory
        test_client.session_factory = TestSessionLocal
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def headers(client: TestClient):

    email = "admin-push@example.com"

    client.post(
        "/auth/register",
        json={"full_name": "Admin", "email": email, "password": "SuperSecret123!"},
    )

    session = client.session_factory()
    try:
        user = session.scalar(select(User).where(User.email == email))
        user.role = UserRole.ADMIN.value
        session.commit()
    finally:
        session.close()

    token = client.post(
        "/auth/login",
        json={"email": email, "password": "SuperSecret123!"},
    ).json()["access_token"]

    return {"Authorization": f"Bearer {token}"}


def _upload(client, headers, name: str, content: str):
    response = client.post(
        "/market-data/upload",
        headers=headers,
        files=[("files", (name, content, "text/csv"))],
    )
    assert response.status_code == 200, response.text
    assert response.json()["errors"] == []


def _saved_dates(client, symbol: str) -> list[str]:
    with open(client.data_directory / f"{symbol}.csv", newline="") as f:
        reader = csv.DictReader(f)
        return [row["datetime"] for row in reader]


def _iso_file(symbol: str, days: range) -> str:
    rows = [
        f"{i},2025-01-{day:02d},NSE:{symbol},100,105,95,{100 + day},1000,0.5,0.4"
        for i, day in enumerate(days)
    ]
    return "\n".join([ISO_HEADER] + rows) + "\n"


def _dayfirst_file(symbol: str, days: range) -> str:
    # Starts on a day > 12 so the day-first format is unambiguous,
    # like the real 3IINFOLTD.csv ("22-04-2005").
    rows = [
        f"{i},{day:02d}-01-2025,NSE:{symbol},100,105,95,{100 + day},1000,0.5,0.4"
        for i, day in enumerate(days)
    ]
    return "\n".join([DAYFIRST_HEADER] + rows) + "\n"


def test_daily_push_adds_the_new_row_to_an_iso_file(client, headers):

    # The bulk upload put 15-24 Jan on the backend.
    _upload(client, headers, "PUSHISO.csv", _iso_file("PUSHISO", range(15, 25)))

    # Next day's push: header + the last 5 local rows, the newest
    # of which (25 Jan) the backend doesn't have yet.
    push = "\n".join(
        [ISO_HEADER]
        + [
            f"{i},2025-01-{day:02d},NSE:PUSHISO,100,105,95,{100 + day},1000,0.5,0.4"
            for i, day in enumerate(range(21, 26), start=6)
        ]
    ) + "\n"
    _upload(client, headers, "PUSHISO.csv", push)

    dates = _saved_dates(client, "PUSHISO")

    assert dates == [f"2025-01-{d:02d}" for d in range(15, 26)]  # 11 rows, once each, in order


def test_daily_push_adds_the_new_row_to_a_dayfirst_file(client, headers):

    _upload(client, headers, "PUSHDMY.csv", _dayfirst_file("PUSHDMY", range(15, 25)))

    push = "\n".join(
        [DAYFIRST_HEADER]
        + [
            f"{i},{day:02d}-01-2025,NSE:PUSHDMY,100,105,95,{100 + day},1000,0.5,0.4"
            for i, day in enumerate(range(21, 26), start=6)
        ]
    ) + "\n"
    _upload(client, headers, "PUSHDMY.csv", push)

    dates = _saved_dates(client, "PUSHDMY")

    assert dates == [f"{d:02d}-01-2025" for d in range(15, 26)]


def test_pushing_the_same_rows_twice_changes_nothing(client, headers):

    _upload(client, headers, "PUSHTWICE.csv", _iso_file("PUSHTWICE", range(15, 25)))

    push = "\n".join(
        [ISO_HEADER]
        + [
            f"{i},2025-01-{day:02d},NSE:PUSHTWICE,100,105,95,{100 + day},1000,0.5,0.4"
            for i, day in enumerate(range(21, 26), start=6)
        ]
    ) + "\n"

    _upload(client, headers, "PUSHTWICE.csv", push)
    first = _saved_dates(client, "PUSHTWICE")

    _upload(client, headers, "PUSHTWICE.csv", push)
    second = _saved_dates(client, "PUSHTWICE")

    assert first == second
    assert len(second) == len(set(second))


def test_a_missed_day_is_repaired_by_the_next_push(client, headers):
    """
    Yesterday's push never arrived, so the backend is missing 25 Jan.
    Today's push carries the last 5 rows (22-26 Jan), which covers
    both days -- that overlap is the whole point of pushing a few
    rows rather than only the newest one.
    """

    _upload(client, headers, "PUSHGAP.csv", _iso_file("PUSHGAP", range(15, 25)))  # ends 24 Jan

    push = "\n".join(
        [ISO_HEADER]
        + [
            f"{i},2025-01-{day:02d},NSE:PUSHGAP,100,105,95,{100 + day},1000,0.5,0.4"
            for i, day in enumerate(range(22, 27), start=7)
        ]
    ) + "\n"
    _upload(client, headers, "PUSHGAP.csv", push)

    dates = _saved_dates(client, "PUSHGAP")

    assert dates == [f"2025-01-{d:02d}" for d in range(15, 27)]


@pytest.mark.parametrize(
    "build_file, build_push, symbol, expected_last",
    [
        (_iso_file, ISO_HEADER, "LOADISO", date(2025, 1, 25)),
        (_dayfirst_file, DAYFIRST_HEADER, "LOADDMY", date(2025, 1, 25)),
    ],
)
def test_merged_file_is_readable_by_the_sync_loader(
    client, headers, build_file, build_push, symbol, expected_last,
):
    """
    The unnamed index column's header is rewritten by the merge
    (pandas turns an empty header into 'Unnamed: 0'); the sync's
    CSVProvider finds columns by name, so it must not care.
    """

    _upload(client, headers, f"{symbol}.csv", build_file(symbol, range(15, 25)))

    style = "{day:02d}-01-2025" if build_file is _dayfirst_file else "2025-01-{day:02d}"
    push = "\n".join(
        [build_push]
        + [
            f"{i},{style.format(day=day)},NSE:{symbol},100,105,95,{100 + day},1000,0.5,0.4"
            for i, day in enumerate(range(21, 26), start=6)
        ]
    ) + "\n"
    _upload(client, headers, f"{symbol}.csv", push)

    provider = CSVProvider(str(client.data_directory))
    candles = provider.fetch_daily_candles(symbol)

    assert len(candles) == 11
    assert candles[-1].trade_date == expected_last
    assert [c.trade_date for c in candles] == sorted(c.trade_date for c in candles)