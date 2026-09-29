"""
End-to-end test of the full daily workflow through the real HTTP
API: register/login -> upload CSVs -> sync -> scan -> scan history.

Uses an isolated in-memory SQLite DB and an isolated temp directory
for CSV storage, so it never touches the real database or the real
data/candles folder.
"""

import os
import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.constants import UserRole
from app.database.base import Base
import app.models  # noqa: F401  (registers all models on Base)
from app.models.user import User


def _generate_candles_csv(
    path: Path,
    symbol: str,
    base_price: float,
    breakout: bool,
    n_days: int = 260,
) -> None:
    """
    Small helper to build a synthetic OHLCV CSV in the project's
    expected format, optionally with a clean breakout pattern in
    the final week (used to give the scan something to match).
    """

    random.seed(42)

    rows = []
    price = base_price
    day = date(2025, 6, 1)

    for i in range(n_days):

        while day.weekday() >= 5:
            day += timedelta(days=1)

        if breakout and i >= n_days - 8:
            change = random.uniform(0.015, 0.035)
        else:
            change = random.uniform(-0.01, 0.01)

        open_price = price
        close_price = round(price * (1 + change), 2)
        high_price = round(
            max(open_price, close_price) * (1 + random.uniform(0, 0.008)), 2
        )
        low_price = round(
            min(open_price, close_price) * (1 - random.uniform(0, 0.008)), 2
        )
        volume = random.randint(500_000, 1_500_000)

        if breakout and i >= n_days - 8:
            volume = int(volume * 2.5)

        rows.append(
            {
                "datetime": day.isoformat(),
                "symbol": f"NSE:{symbol}",
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": volume,
            }
        )

        price = close_price
        day += timedelta(days=1)

    pd.DataFrame(rows).to_csv(path, index=False)


@pytest.fixture
def client(tmp_path, monkeypatch):
    """
    A TestClient wired to an isolated in-memory SQLite DB and an
    isolated temp CSV directory, so this test never touches the
    real database or the real data/candles folder.
    """

    data_directory = tmp_path / "candles"
    data_directory.mkdir()

    from app.config.settings import settings as app_settings

    monkeypatch.setattr(
        app_settings,
        "DATA_DIRECTORY",
        str(data_directory),
    )

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSessionLocal = sessionmaker(bind=engine)

    # Imported after DATA_DIRECTORY is set, and inside the fixture,
    # so app.config.settings picks up the env var when it's loaded.
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


def _register_and_login(client: TestClient, email: str) -> str:

    client.post(
        "/auth/register",
        json={
            "full_name": "Test Admin",
            "email": email,
            "password": "SuperSecret123!",
        },
    )

    response = client.post(
        "/auth/login",
        json={"email": email, "password": "SuperSecret123!"},
    )

    assert response.status_code == 200, response.text

    return response.json()["access_token"]


def _promote_to_admin(client: TestClient, email: str) -> None:
    """
    Registration always creates a regular user (by design -- there
    is intentionally no public endpoint to self-register as admin).
    Promote directly in the DB, mirroring how a real deployment
    would seed its first admin account.
    """

    session = client.session_factory()

    try:
        user = session.scalar(select(User).where(User.email == email))
        user.role = UserRole.ADMIN.value
        session.commit()
    finally:
        session.close()


def test_upload_sync_scan_flow(client: TestClient):

    email = "admin@example.com"

    token = _register_and_login(client, email)
    _promote_to_admin(client, email)

    # Re-login so the token reflects the promoted role, matching
    # how a real client would need a fresh token after a role change.
    token = _register_and_login(client, email)

    headers = {"Authorization": f"Bearer {token}"}

    # --- Step 1: generate and upload two synthetic CSVs ---
    breakout_csv = client.data_directory.parent / "BREAKOUTCO.csv"
    flat_csv = client.data_directory.parent / "FLATCO.csv"

    _generate_candles_csv(breakout_csv, "BREAKOUTCO", 250, breakout=True)
    _generate_candles_csv(flat_csv, "FLATCO", 500, breakout=False)

    with open(breakout_csv, "rb") as f1, open(flat_csv, "rb") as f2:
        files = [
            ("files", ("BREAKOUTCO.csv", f1.read(), "text/csv")),
            ("files", ("FLATCO.csv", f2.read(), "text/csv")),
        ]

    response = client.post(
        "/market-data/upload",
        files=files,
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["saved"]) == 2
    assert body["errors"] == []

    # --- Step 2: sync (process CSVs into indicators/features) ---
    response = client.post("/market-data/sync", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json() == {"status": "completed"}

    # --- Step 3: scan ---
    scan_request = {
        "strategy_name": "Breakout Scan",
        "expression": {
            "operator": "AND",
            "children": [
                {
                    "left": "EMA20",
                    "operator": "crosses_above",
                    "right": "EMA50",
                },
            ],
        },
    }

    response = client.post(
        "/scanner/scan",
        json=scan_request,
        headers=headers,
    )

    assert response.status_code == 200, response.text
    results = response.json()
    assert isinstance(results, list)

    # --- Step 4: scan history was persisted ---
    response = client.get("/scanner/runs", headers=headers)
    assert response.status_code == 200, response.text

    page = response.json()
    assert page["total"] == 1
    assert len(page["runs"]) == 1
    assert page["runs"][0]["strategy"] == "Breakout Scan"
    assert page["runs"][0]["stocks_scanned"] == 2

    run_id = page["runs"][0]["id"]

    response = client.get(f"/scanner/runs/{run_id}", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["id"] == run_id


def test_scanner_and_market_data_endpoints_require_auth(client: TestClient):

    response = client.post(
        "/scanner/scan",
        json={
            "expression": {"operator": "AND", "children": []},
        },
    )
    assert response.status_code in (401, 403)

    response = client.post("/market-data/sync")
    assert response.status_code in (401, 403)


def test_market_data_endpoints_require_admin_not_just_user(client: TestClient):

    email = "regular-user@example.com"
    token = _register_and_login(client, email)
    headers = {"Authorization": f"Bearer {token}"}

    # A regular (non-admin) user can scan...
    response = client.post(
        "/scanner/scan",
        json={
            "expression": {"operator": "AND", "children": []},
        },
        headers=headers,
    )
    assert response.status_code == 200

    # ...but cannot trigger a sync.
    response = client.post("/market-data/sync", headers=headers)
    assert response.status_code == 403