from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.models.feature.definition import FeatureDefinition
from app.models.feature.value import FeatureValue
from app.models.instrument import Instrument
from app.repositories.feature_value_repository import (
    FeatureValueRepository,
)


def create_session():

    engine = create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)

    return Session()


def create_instrument(session):

    instrument = Instrument(
        symbol="RELIANCE",
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


def create_feature_definition(session, name="EMA20"):

    feature = FeatureDefinition(
        name=name,
        category="trend",
        data_type="decimal",
        description=name,
    )

    session.add(feature)
    session.commit()

    return feature


def test_bulk_upsert_inserts_new_rows():

    session = create_session()

    instrument = create_instrument(session)
    feature = create_feature_definition(session)

    repository = FeatureValueRepository(session)

    repository.bulk_upsert(
        [
            FeatureValue(
                instrument_id=instrument.id,
                feature_definition_id=feature.id,
                trade_date=date(2026, 8, 9),
                decimal_value=Decimal("105"),
            )
        ]
    )
    session.commit()

    rows = session.scalars(select(FeatureValue)).all()

    assert len(rows) == 1
    assert rows[0].decimal_value == Decimal("105")


def test_bulk_upsert_updates_existing_row_instead_of_crashing():
    """
    Regression test: re-running the pipeline for an instrument that
    already has data (e.g. a daily re-upload of an updated CSV)
    should update the existing value, not raise a unique constraint
    violation.
    """

    session = create_session()

    instrument = create_instrument(session)
    feature = create_feature_definition(session)

    repository = FeatureValueRepository(session)

    repository.bulk_upsert(
        [
            FeatureValue(
                instrument_id=instrument.id,
                feature_definition_id=feature.id,
                trade_date=date(2026, 8, 9),
                decimal_value=Decimal("105"),
            )
        ]
    )
    session.commit()

    # Re-run with a corrected/updated value for the same day.
    repository.bulk_upsert(
        [
            FeatureValue(
                instrument_id=instrument.id,
                feature_definition_id=feature.id,
                trade_date=date(2026, 8, 9),
                decimal_value=Decimal("106.5"),
            )
        ]
    )
    session.commit()

    rows = session.scalars(select(FeatureValue)).all()

    assert len(rows) == 1
    assert rows[0].decimal_value == Decimal("106.5")