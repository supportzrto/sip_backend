from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.models.feature.definition import FeatureDefinition
from app.models.feature.value import FeatureValue
from app.models.instrument import Instrument
from app.repositories.feature_value_repository import (
    FeatureValueRepository,
)


def create_session():

    engine = create_engine(
        "sqlite:///:memory:"
    )

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


def create_feature(session):

    feature = FeatureDefinition(

        name="EMA20",

        category="TREND",

        data_type="DECIMAL",

        description="20 EMA",

        created_at=datetime.now(UTC),

        updated_at=datetime.now(UTC),
    )

    session.add(feature)

    session.commit()

    return feature


def test_bulk_insert():

    session = create_session()

    repository = FeatureValueRepository(session)

    instrument = create_instrument(session)

    feature = create_feature(session)

    values = [

        FeatureValue(

            instrument_id=instrument.id,

            feature_definition_id=feature.id,

            trade_date=date(2026, 1, 1),

            decimal_value=Decimal("100.50"),

        ),

        FeatureValue(

            instrument_id=instrument.id,

            feature_definition_id=feature.id,

            trade_date=date(2026, 1, 2),

            decimal_value=Decimal("101.25"),

        ),

    ]

    repository.bulk_insert(values)

    session.commit()

    history = repository.get_history(

        instrument.id,

        feature.id,

    )

    assert len(history) == 2


def test_get_history():

    session = create_session()

    repository = FeatureValueRepository(session)

    instrument = create_instrument(session)

    feature = create_feature(session)

    repository.bulk_insert(

        [

            FeatureValue(

                instrument_id=instrument.id,

                feature_definition_id=feature.id,

                trade_date=date(2026, 1, 1),

                decimal_value=Decimal("100"),

            ),

            FeatureValue(

                instrument_id=instrument.id,

                feature_definition_id=feature.id,

                trade_date=date(2026, 1, 2),

                decimal_value=Decimal("110"),

            ),

            FeatureValue(

                instrument_id=instrument.id,

                feature_definition_id=feature.id,

                trade_date=date(2026, 1, 3),

                decimal_value=Decimal("120"),

            ),

        ]

    )

    session.commit()

    history = repository.get_history(

        instrument.id,

        feature.id,

    )

    assert len(history) == 3

    assert history[0].decimal_value == Decimal("100")

    assert history[1].decimal_value == Decimal("110")

    assert history[2].decimal_value == Decimal("120")


def test_delete_history():

    session = create_session()

    repository = FeatureValueRepository(session)

    instrument = create_instrument(session)

    feature = create_feature(session)

    repository.bulk_insert(

        [

            FeatureValue(

                instrument_id=instrument.id,

                feature_definition_id=feature.id,

                trade_date=date(2026, 1, 1),

                decimal_value=Decimal("100"),

            ),

            FeatureValue(

                instrument_id=instrument.id,

                feature_definition_id=feature.id,

                trade_date=date(2026, 1, 2),

                decimal_value=Decimal("110"),

            ),

        ]

    )

    session.commit()

    repository.delete_history(

        instrument.id
    )

    session.commit()

    history = repository.get_history(

        instrument.id,

        feature.id,

    )

    assert history == []