"""
bulk_upsert must never rewrite a row whose values are unchanged (in
Postgres a rewrite leaves a dead row version and dead index entries
behind -- see test_incremental_write_window.py for how that filled a
volume), while still applying every real change, including to and
from NULL. This file checks the behaviour on SQLite as part of the
normal suite; test_feature_value_upsert_postgres.py proves the
no-rewrite part on a real Postgres when one is available.
"""

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.models.feature.definition import FeatureDefinition
from app.models.feature.value import FeatureValue
from app.models.instrument import Instrument
from app.repositories.feature_value_repository import FeatureValueRepository

DAY = date(2026, 1, 5)


def make_repository():

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    now = datetime.now(UTC)

    session.add(
        Instrument(
            symbol="AAA", company_name="AAA", exchange="NSE",
            instrument_type="EQUITY", provider="CSV", is_active=True,
            created_at=now, updated_at=now,
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

    ids = {
        name: session.scalar(select(FeatureDefinition.id).where(FeatureDefinition.name == name))
        for name in ("RSI_14", "VOLUME", "UP")
    }
    instrument_id = session.scalar(select(Instrument.id))

    return FeatureValueRepository(session), session, ids, instrument_id


def value(instrument_id, feature_id, **kwargs) -> FeatureValue:
    return FeatureValue(
        instrument_id=instrument_id,
        feature_definition_id=feature_id,
        trade_date=DAY,
        **kwargs,
    )


def stored(session, feature_id):
    row = session.scalar(
        select(FeatureValue).where(FeatureValue.feature_definition_id == feature_id),
    )
    session.refresh(row)
    return row


def test_identical_upsert_leaves_one_row_with_the_same_values():

    repo, session, ids, inst = make_repository()
    batch = lambda: [value(inst, ids["RSI_14"], decimal_value=Decimal("55.5"))]  # noqa: E731

    repo.bulk_upsert(batch()); session.commit()
    repo.bulk_upsert(batch()); session.commit()

    assert session.scalar(select(func.count()).select_from(FeatureValue)) == 1
    assert stored(session, ids["RSI_14"]).decimal_value == Decimal("55.5")


def test_a_changed_value_is_applied():

    repo, session, ids, inst = make_repository()

    repo.bulk_upsert([value(inst, ids["RSI_14"], decimal_value=Decimal("55.5"))]); session.commit()
    repo.bulk_upsert([value(inst, ids["RSI_14"], decimal_value=Decimal("61.25"))]); session.commit()

    assert float(stored(session, ids["RSI_14"]).decimal_value) == 61.25


def test_null_to_value_and_value_to_null_are_both_applied():

    repo, session, ids, inst = make_repository()

    repo.bulk_upsert([value(inst, ids["RSI_14"], decimal_value=None)]); session.commit()
    repo.bulk_upsert([value(inst, ids["RSI_14"], decimal_value=Decimal("40"))]); session.commit()
    assert float(stored(session, ids["RSI_14"]).decimal_value) == 40.0

    repo.bulk_upsert([value(inst, ids["RSI_14"], decimal_value=None)]); session.commit()
    assert stored(session, ids["RSI_14"]).decimal_value is None


def test_integer_and_boolean_changes_are_applied():

    repo, session, ids, inst = make_repository()

    repo.bulk_upsert([
        value(inst, ids["VOLUME"], integer_value=1000),
        value(inst, ids["UP"], boolean_value=False),
    ]); session.commit()

    repo.bulk_upsert([
        value(inst, ids["VOLUME"], integer_value=1500),
        value(inst, ids["UP"], boolean_value=True),
    ]); session.commit()

    assert stored(session, ids["VOLUME"]).integer_value == 1500
    assert stored(session, ids["UP"]).boolean_value is True