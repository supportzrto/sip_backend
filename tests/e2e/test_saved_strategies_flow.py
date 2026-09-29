"""
End-to-end tests of the /strategies API (custom saved scan
expressions) and how alert rules can reference them instead of a
built-in strategy_key.

Uses an isolated in-memory SQLite DB, same pattern as
test_upload_sync_scan_flow.py / test_watchlists_and_alerts_flow.py.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
import app.models  # noqa: F401  (registers all models on Base)


SAMPLE_EXPRESSION = {
    "operator": "AND",
    "children": [
        {"left": "RSI14", "operator": "<", "right": "30"},
    ],
}


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


def test_saved_strategy_crud_flow(client: TestClient):

    token = _register_and_login(client, "strategy-user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Create
    response = client.post(
        "/strategies",
        json={"name": "My Custom Setup", "expression": SAMPLE_EXPRESSION},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    strategy = response.json()
    assert strategy["name"] == "My Custom Setup"
    assert strategy["expression"]["operator"] == "AND"

    strategy_id = strategy["id"]

    # List
    response = client.get("/strategies", headers=headers)
    assert response.status_code == 200
    assert len(response.json()["strategies"]) == 1

    # Get
    response = client.get(f"/strategies/{strategy_id}", headers=headers)
    assert response.status_code == 200

    # Update the name
    response = client.patch(
        f"/strategies/{strategy_id}",
        json={"name": "Renamed Setup"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Renamed Setup"

    # Run it now -- no instruments/features exist, so this should
    # just return an empty match list rather than error.
    response = client.post(
        f"/strategies/{strategy_id}/scan", headers=headers,
    )
    assert response.status_code == 200, response.text
    assert response.json() == []

    # Delete
    response = client.delete(f"/strategies/{strategy_id}", headers=headers)
    assert response.status_code == 204

    response = client.get(f"/strategies/{strategy_id}", headers=headers)
    assert response.status_code == 404


def test_saved_strategy_ownership_is_enforced(client: TestClient):

    owner_token = _register_and_login(client, "owner2@example.com")
    other_token = _register_and_login(client, "other2@example.com")

    response = client.post(
        "/strategies",
        json={"name": "My Custom Setup", "expression": SAMPLE_EXPRESSION},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    strategy_id = response.json()["id"]

    other_headers = {"Authorization": f"Bearer {other_token}"}

    response = client.get(
        f"/strategies/{strategy_id}", headers=other_headers,
    )
    assert response.status_code == 404

    response = client.delete(
        f"/strategies/{strategy_id}", headers=other_headers,
    )
    assert response.status_code == 404


def test_duplicate_saved_strategy_name_is_rejected(client: TestClient):

    token = _register_and_login(client, "dup-strategy@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    client.post(
        "/strategies",
        json={"name": "My Custom Setup", "expression": SAMPLE_EXPRESSION},
        headers=headers,
    )

    response = client.post(
        "/strategies",
        json={"name": "My Custom Setup", "expression": SAMPLE_EXPRESSION},
        headers=headers,
    )
    assert response.status_code == 409


def test_alert_rule_can_use_a_saved_strategy_instead_of_strategy_key(
    client: TestClient,
):

    token = _register_and_login(client, "alert-saved-strategy@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/strategies",
        json={"name": "My Custom Setup", "expression": SAMPLE_EXPRESSION},
        headers=headers,
    )
    strategy_id = response.json()["id"]

    response = client.post(
        "/alerts",
        json={"name": "Custom Alert", "saved_strategy_id": strategy_id},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    rule = response.json()
    assert rule["saved_strategy_id"] == strategy_id
    assert rule["strategy_key"] is None


def test_alert_rule_rejects_both_strategy_sources_at_once(
    client: TestClient,
):

    token = _register_and_login(client, "both-sources@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/strategies",
        json={"name": "My Custom Setup", "expression": SAMPLE_EXPRESSION},
        headers=headers,
    )
    strategy_id = response.json()["id"]

    response = client.post(
        "/alerts",
        json={
            "name": "Ambiguous",
            "strategy_key": "breakout",
            "saved_strategy_id": strategy_id,
        },
        headers=headers,
    )
    assert response.status_code == 422  # pydantic validation error


def test_alert_rule_rejects_neither_strategy_source(client: TestClient):

    token = _register_and_login(client, "neither-source@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/alerts",
        json={"name": "Ambiguous"},
        headers=headers,
    )
    assert response.status_code == 422


def test_alert_rule_rejects_saved_strategy_not_owned_by_caller(
    client: TestClient,
):

    owner_token = _register_and_login(client, "strat-owner@example.com")
    other_token = _register_and_login(client, "strat-other@example.com")

    response = client.post(
        "/strategies",
        json={"name": "My Custom Setup", "expression": SAMPLE_EXPRESSION},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    strategy_id = response.json()["id"]

    response = client.post(
        "/alerts",
        json={"name": "Sneaky", "saved_strategy_id": strategy_id},
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert response.status_code == 404