"""
Repeated-request sanity check for the scanner API.

IMPORTANT LIMITATION: this test intentionally does NOT use real
multi-threaded concurrency. This test suite runs against an
in-memory SQLite database, and raw sqlite3 connections are not
reliably safe under true concurrent multi-threaded access -- trying
to exercise that here produces flaky failures and deadlocks that
are an artifact of the SQLite test setup, not of the application
code (production uses Postgres, which handles real concurrent
connections properly).

What this test DOES verify: many requests in a row, each with their
own DB session (matching how a real request lifecycle works), all
succeed and don't leak state between requests or leave the DB in
a bad state.

Real concurrent-load behavior (many simultaneous requests against a
real Postgres instance) needs to be tested separately with a tool
like locust or k6 against a staging deployment -- that's outside
what a unit/integration test in this repo can meaningfully cover.
"""

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
import app.models  # noqa: F401


def test_repeated_scan_requests_succeed_and_are_all_persisted(monkeypatch, tmp_path):

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

    with TestClient(app) as client:

        client.post(
            "/auth/register",
            json={
                "full_name": "Test User",
                "email": "repeat@example.com",
                "password": "SuperSecret123!",
            },
        )

        login = client.post(
            "/auth/login",
            json={
                "email": "repeat@example.com",
                "password": "SuperSecret123!",
            },
        )
        assert login.status_code == 200
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        scan_request = {
            "expression": {"operator": "AND", "children": []},
        }

        statuses = []

        for _ in range(20):
            response = client.post(
                "/scanner/scan",
                json=scan_request,
                headers=headers,
            )
            statuses.append(response.status_code)

        assert all(status == 200 for status in statuses)

        runs_response = client.get(
            "/scanner/runs?limit=100",
            headers=headers,
        )
        assert runs_response.status_code == 200
        assert runs_response.json()["total"] == 20

    app.dependency_overrides.clear()