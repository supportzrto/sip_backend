"""
POST /market-data/upload used to sort each symbol's merged file by
the raw "datetime" column as TEXT, not as a real date. That's
silently correct for ISO-formatted files (YYYY-MM-DD sorts correctly
as text) but silently WRONG for day-first files (DD-MM-YYYY does
not), scrambling that symbol's row order -- which then corrupts
every indicator computed from it downstream, since they all assume
chronological order.

These tests upload CSVs with rows deliberately out of order and
confirm the saved file on disk ends up in true chronological order,
for both date styles actually present in data/candles/ (2503 files
ISO, 1 file day-first, confirmed by inspecting the real data).
"""

import csv
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.constants import UserRole
from app.database.base import Base
import app.models  # noqa: F401  (registers all models on Base)
from app.models.user import User
from sqlalchemy import select


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


def _register_admin(client: TestClient, email: str) -> str:

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

    response = client.post(
        "/auth/login",
        json={"email": email, "password": "SuperSecret123!"},
    )
    return response.json()["access_token"]


def _rows_from(path: Path) -> list[list[str]]:
    with open(path, newline="") as f:
        reader = csv.reader(f)
        next(reader)  # header
        return list(reader)


def test_upload_sorts_day_first_dates_chronologically(client: TestClient):
    """
    The exact bug case: a day-first file (like the real
    3IINFOLTD.csv) uploaded with rows out of order must come out
    truly chronological, not text-sorted.
    """

    token = _register_admin(client, "admin-dayfirst@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Deliberately out of order, and chosen so a plain text sort
    # would get it wrong: "15-01-2024" vs "05-01-2025" -- Jan 2024
    # is earlier, but "15" > "05" as text, so a string sort would
    # wrongly put 2025 first.
    csv_content = (
        "datetime,symbol,open,high,low,close,volume\n"
        "05-01-2025,NSE:DAYFIRST,100,105,99,104,1000\n"
        "15-01-2024,NSE:DAYFIRST,90,95,89,94,2000\n"
        "01-06-2024,NSE:DAYFIRST,95,100,94,99,1500\n"
    )

    response = client.post(
        "/market-data/upload",
        headers=headers,
        files=[("files", ("DAYFIRST.csv", csv_content, "text/csv"))],
    )
    assert response.status_code == 200, response.text
    assert response.json()["errors"] == []

    saved_path = client.data_directory / "DAYFIRST.csv"
    dates = [row[0] for row in _rows_from(saved_path)]

    assert dates == ["15-01-2024", "01-06-2024", "05-01-2025"]


def test_upload_sorts_iso_dates_chronologically(client: TestClient):
    """
    Regression check: the ~2500 ISO-formatted files must keep
    working exactly as before.
    """

    token = _register_admin(client, "admin-iso@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    csv_content = (
        "datetime,symbol,open,high,low,close,volume\n"
        "2025-01-05,NSE:ISOSYM,100,105,99,104,1000\n"
        "2024-01-15,NSE:ISOSYM,90,95,89,94,2000\n"
        "2024-06-01,NSE:ISOSYM,95,100,94,99,1500\n"
    )

    response = client.post(
        "/market-data/upload",
        headers=headers,
        files=[("files", ("ISOSYM.csv", csv_content, "text/csv"))],
    )
    assert response.status_code == 200, response.text

    saved_path = client.data_directory / "ISOSYM.csv"
    dates = [row[0] for row in _rows_from(saved_path)]

    assert dates == ["2024-01-15", "2024-06-01", "2025-01-05"]


def test_upload_merge_preserves_correct_order_for_day_first_file(client: TestClient):
    """
    The realistic path for the bulk backfill: an existing day-first
    file on disk gets a second upload merged into it (e.g. a re-run
    after an interrupted batch). The merged result must still be in
    true chronological order, not just the first upload.
    """

    token = _register_admin(client, "admin-merge@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    first = (
        "datetime,symbol,open,high,low,close,volume\n"
        "01-01-2024,NSE:MERGEME,90,95,89,94,2000\n"
        "15-01-2024,NSE:MERGEME,91,96,90,95,2100\n"
    )
    response = client.post(
        "/market-data/upload",
        headers=headers,
        files=[("files", ("MERGEME.csv", first, "text/csv"))],
    )
    assert response.status_code == 200, response.text

    # A second, later-dated batch, deliberately out of order.
    second = (
        "datetime,symbol,open,high,low,close,volume\n"
        "01-03-2024,NSE:MERGEME,93,98,92,97,2200\n"
        "01-02-2024,NSE:MERGEME,92,97,91,96,2150\n"
    )
    response = client.post(
        "/market-data/upload",
        headers=headers,
        files=[("files", ("MERGEME.csv", second, "text/csv"))],
    )
    assert response.status_code == 200, response.text

    saved_path = client.data_directory / "MERGEME.csv"
    dates = [row[0] for row in _rows_from(saved_path)]

    assert dates == ["01-01-2024", "15-01-2024", "01-02-2024", "01-03-2024"]


def test_upload_deduplicates_same_date_keeping_latest(client: TestClient):
    """
    Confirms the fix didn't disturb the existing dedup-by-date
    behaviour (unrelated to the sort key, but exercised by the same
    code path, so worth locking in).
    """

    token = _register_admin(client, "admin-dedup@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    first = (
        "datetime,symbol,open,high,low,close,volume\n"
        "2025-01-05,NSE:DEDUPME,100,105,99,104,1000\n"
    )
    client.post(
        "/market-data/upload",
        headers=headers,
        files=[("files", ("DEDUPME.csv", first, "text/csv"))],
    )

    # Same date, updated close price -- should replace, not duplicate.
    second = (
        "datetime,symbol,open,high,low,close,volume\n"
        "2025-01-05,NSE:DEDUPME,100,105,99,110,1200\n"
    )
    response = client.post(
        "/market-data/upload",
        headers=headers,
        files=[("files", ("DEDUPME.csv", second, "text/csv"))],
    )
    assert response.status_code == 200, response.text

    saved_path = client.data_directory / "DEDUPME.csv"
    rows = _rows_from(saved_path)

    assert len(rows) == 1
    assert rows[0][0] == "2025-01-05"
    assert rows[0][5] == "110"  # close column, the updated value