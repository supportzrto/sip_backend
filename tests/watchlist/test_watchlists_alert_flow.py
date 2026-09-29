"""
End-to-end tests of the watchlists and alerts HTTP API: CRUD,
ownership scoping (a resource belonging to someone else 404s, same
as /scanner/runs), and input validation.

Uses an isolated in-memory SQLite DB, same pattern as
test_upload_sync_scan_flow.py.
"""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
import app.models  # noqa: F401  (registers all models on Base)
from app.models.instrument import Instrument


@pytest.fixture
def client(tmp_path, monkeypatch):

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
        test_client.session_factory = TestSessionLocal
        yield test_client

    app.dependency_overrides.clear()


def _register_and_login(client: TestClient, email: str) -> str:

    client.post(
        "/auth/register",
        json={
            "full_name": "Test User",
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


def _create_instrument(client: TestClient, symbol: str = "RELIANCE"):

    session = client.session_factory()

    try:
        instrument = Instrument(
            symbol=symbol,
            company_name=f"{symbol} Ltd",
            exchange="NSE",
            instrument_type="EQ",
            isin=f"INE{symbol}01018"[:12],
            provider="NSE",
            provider_token=symbol,
            is_active=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(instrument)
        session.commit()
    finally:
        session.close()


def test_watchlist_crud_flow(client: TestClient):

    token = _register_and_login(client, "watchlist-user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    _create_instrument(client, "RELIANCE")

    # Create
    response = client.post(
        "/watchlists", json={"name": "My Longs"}, headers=headers,
    )
    assert response.status_code == 201, response.text
    watchlist = response.json()
    assert watchlist["name"] == "My Longs"
    assert watchlist["items"] == []

    watchlist_id = watchlist["id"]

    # List
    response = client.get("/watchlists", headers=headers)
    assert response.status_code == 200
    assert len(response.json()["watchlists"]) == 1

    # Add an item
    response = client.post(
        f"/watchlists/{watchlist_id}/items",
        json={"symbol": "RELIANCE"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    item = response.json()
    assert item["symbol"] == "RELIANCE"

    # Duplicate item -> 409
    response = client.post(
        f"/watchlists/{watchlist_id}/items",
        json={"symbol": "RELIANCE"},
        headers=headers,
    )
    assert response.status_code == 409

    # Unknown symbol -> 404
    response = client.post(
        f"/watchlists/{watchlist_id}/items",
        json={"symbol": "NOPE"},
        headers=headers,
    )
    assert response.status_code == 404

    # Get reflects the item
    response = client.get(f"/watchlists/{watchlist_id}", headers=headers)
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1

    # Remove the item
    response = client.delete(
        f"/watchlists/{watchlist_id}/items/{item['id']}",
        headers=headers,
    )
    assert response.status_code == 204

    response = client.get(f"/watchlists/{watchlist_id}", headers=headers)
    assert response.json()["items"] == []

    # Delete the watchlist
    response = client.delete(
        f"/watchlists/{watchlist_id}", headers=headers,
    )
    assert response.status_code == 204

    response = client.get(f"/watchlists/{watchlist_id}", headers=headers)
    assert response.status_code == 404


def test_watchlist_ownership_is_enforced(client: TestClient):

    owner_token = _register_and_login(client, "owner@example.com")
    other_token = _register_and_login(client, "other@example.com")

    response = client.post(
        "/watchlists",
        json={"name": "My Longs"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    watchlist_id = response.json()["id"]

    other_headers = {"Authorization": f"Bearer {other_token}"}

    response = client.get(
        f"/watchlists/{watchlist_id}", headers=other_headers,
    )
    assert response.status_code == 404

    response = client.delete(
        f"/watchlists/{watchlist_id}", headers=other_headers,
    )
    assert response.status_code == 404


def test_duplicate_watchlist_name_for_same_user_is_rejected(
    client: TestClient,
):

    token = _register_and_login(client, "dup-name@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    client.post("/watchlists", json={"name": "My Longs"}, headers=headers)

    response = client.post(
        "/watchlists", json={"name": "My Longs"}, headers=headers,
    )
    assert response.status_code == 409


def test_alert_rule_crud_flow(client: TestClient):

    token = _register_and_login(client, "alert-user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Create
    response = client.post(
        "/alerts",
        json={"name": "Breakout Alert", "strategy_key": "breakout"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    rule = response.json()
    assert rule["strategy_key"] == "breakout"
    assert rule["is_active"] is True
    assert rule["last_matched_symbols"] == []

    rule_id = rule["id"]

    # List
    response = client.get("/alerts", headers=headers)
    assert response.status_code == 200
    assert len(response.json()["alerts"]) == 1

    # Get
    response = client.get(f"/alerts/{rule_id}", headers=headers)
    assert response.status_code == 200

    # Update (pause it)
    response = client.patch(
        f"/alerts/{rule_id}",
        json={"is_active": False},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    # Delete
    response = client.delete(f"/alerts/{rule_id}", headers=headers)
    assert response.status_code == 204

    response = client.get(f"/alerts/{rule_id}", headers=headers)
    assert response.status_code == 404


def test_alert_rule_rejects_unknown_strategy_key(client: TestClient):

    token = _register_and_login(client, "bad-strategy@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/alerts",
        json={"name": "Bad", "strategy_key": "not-a-real-strategy"},
        headers=headers,
    )
    assert response.status_code == 400


def test_alert_rule_rejects_watchlist_not_owned_by_caller(
    client: TestClient,
):

    owner_token = _register_and_login(client, "wl-owner@example.com")
    other_token = _register_and_login(client, "wl-other@example.com")

    response = client.post(
        "/watchlists",
        json={"name": "My Longs"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    watchlist_id = response.json()["id"]

    response = client.post(
        "/alerts",
        json={
            "name": "Sneaky",
            "strategy_key": "breakout",
            "watchlist_id": watchlist_id,
        },
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert response.status_code == 404


def test_alert_rule_notifications_endpoint_starts_empty(
    client: TestClient,
):

    token = _register_and_login(client, "notif-user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/alerts/notifications/recent", headers=headers)
    assert response.status_code == 200
    assert response.json()["notifications"] == []


def test_watchlist_and_alert_endpoints_require_auth(client: TestClient):

    response = client.get("/watchlists")
    assert response.status_code in (401, 403)

    response = client.post(
        "/alerts",
        json={"name": "X", "strategy_key": "breakout"},
    )
    assert response.status_code in (401, 403)