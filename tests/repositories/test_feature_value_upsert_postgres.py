"""
Proof, on a REAL PostgreSQL, that bulk_upsert does not rewrite rows
whose values are unchanged. SQLite can't show this -- the raw SQL
path only runs on Postgres, and "rewritten" means a new row version
(visible as a changed xmin).

Skipped unless TEST_POSTGRES_URL is set, e.g.

    TEST_POSTGRES_URL=postgresql+psycopg://user:pass@localhost:5432/anydb

It only ever works inside a throwaway schema it creates and drops
itself, so it is safe to point at a database that has real tables --
nothing outside that schema is read or written.
"""

import os
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
import app.models  # noqa: F401  (registers all models on Base)
from app.models.feature.definition import FeatureDefinition
from app.models.feature.value import FeatureValue
from app.models.instrument import Instrument
from app.repositories.feature_value_repository import FeatureValueRepository

POSTGRES_URL = os.getenv("TEST_POSTGRES_URL")

pytestmark = pytest.mark.skipif(
    not POSTGRES_URL, reason="set TEST_POSTGRES_URL to run against a real PostgreSQL",
)


@pytest.fixture
def pg():

    schema = f"upsert_test_{uuid4().hex[:8]}"

    admin = create_engine(POSTGRES_URL, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))

    engine = create_engine(POSTGRES_URL, connect_args={"options": f"-csearch_path={schema}"})
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    now = datetime.now(UTC)
    session.add(
        Instrument(
            symbol="AAA", company_name="AAA", exchange="NSE", instrument_type="EQUITY",
            provider="CSV", is_active=True, created_at=now, updated_at=now,
        )
    )
    for name, data_type in (("RSI_14", "decimal"), ("VOLUME", "integer"), ("UP", "boolean")):
        session.add(
            FeatureDefinition(
                name=name, category="test", data_type=data_type,
                description=name, created_at=now, updated_at=now,
            )
        )
    session.commit()

    instrument_id = session.execute(text("select id from instruments")).scalar()
    ids = {name: fid for fid, name in session.execute(text("select id, name from feature_definitions"))}

    yield session, FeatureValueRepository(session), ids, instrument_id

    session.close()
    engine.dispose()
    with admin.connect() as conn:
        conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    admin.dispose()


def rows(inst, ids, days, bump_day=None):

    out = []
    for d in range(1, days + 1):
        day = date(2026, 1, d)
        out.append(FeatureValue(
            instrument_id=inst, feature_definition_id=ids["RSI_14"], trade_date=day,
            decimal_value=Decimal("50") + d + (Decimal("0.5") if d == bump_day else 0),
        ))
        out.append(FeatureValue(
            instrument_id=inst, feature_definition_id=ids["VOLUME"], trade_date=day,
            integer_value=1000 + d,
        ))
        out.append(FeatureValue(
            instrument_id=inst, feature_definition_id=ids["UP"], trade_date=day,
            boolean_value=(d % 2 == 0),
        ))
    return out


def versions(session):
    return {r[0]: r[1] for r in session.execute(text("select id, xmin::text from feature_values"))}


def test_identical_upsert_rewrites_nothing(pg):

    session, repo, ids, inst = pg

    repo.bulk_upsert(rows(inst, ids, 20)); session.commit()
    before = versions(session)

    repo.bulk_upsert(rows(inst, ids, 20)); session.commit()
    after = versions(session)

    assert len(before) == len(after) == 60
    assert before == after  # every row kept its row version: nothing was rewritten


def test_only_the_changed_row_is_rewritten(pg):

    session, repo, ids, inst = pg

    repo.bulk_upsert(rows(inst, ids, 20)); session.commit()
    before = versions(session)

    repo.bulk_upsert(rows(inst, ids, 20, bump_day=7)); session.commit()
    after = versions(session)

    assert [k for k in before if before[k] != after[k]] == [
        session.execute(text(
            "select id from feature_values where trade_date = '2026-01-07' and feature_definition_id = :f"
        ), {"f": ids["RSI_14"]}).scalar()
    ]


def test_new_days_are_added_without_touching_older_rows(pg):

    session, repo, ids, inst = pg

    repo.bulk_upsert(rows(inst, ids, 20)); session.commit()
    before = versions(session)

    repo.bulk_upsert(rows(inst, ids, 23)); session.commit()
    after = versions(session)

    assert len(after) - len(before) == 9  # 3 new days x 3 features
    assert all(after[k] == before[k] for k in before)


def test_changes_to_and_from_null_are_still_applied(pg):

    session, repo, ids, inst = pg

    repo.bulk_upsert(rows(inst, ids, 5)); session.commit()

    session.execute(text(
        "update feature_values set boolean_value = NULL where trade_date = '2026-01-02' and feature_definition_id = :f"
    ), {"f": ids["UP"]})
    session.commit()

    repo.bulk_upsert(rows(inst, ids, 5)); session.commit()

    assert session.execute(text(
        "select boolean_value from feature_values where trade_date = '2026-01-02' and feature_definition_id = :f"
    ), {"f": ids["UP"]}).scalar() is True

    repo.bulk_upsert([FeatureValue(
        instrument_id=inst, feature_definition_id=ids["RSI_14"], trade_date=date(2026, 1, 3),
        decimal_value=None,
    )]); session.commit()

    assert session.execute(text(
        "select decimal_value from feature_values where trade_date = '2026-01-03' and feature_definition_id = :f"
    ), {"f": ids["RSI_14"]}).scalar() is None