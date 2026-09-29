from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.feature_store.cache import FeatureIdCache
from app.feature_store.mapper import FeatureValueMapper
from app.models.feature.definition import FeatureDefinition
from app.repositories.feature_definition_repository import (
    FeatureDefinitionRepository,
)


def create_session():

    engine = create_engine(
        "sqlite:///:memory:"
    )

    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)

    return Session()


def seed_features(session):

    features = [

        FeatureDefinition(

            name="EMA20",

            category="TREND",

            data_type="DECIMAL",

            description="20 EMA",

            created_at=datetime.now(UTC),

            updated_at=datetime.now(UTC),
        ),

        FeatureDefinition(

            name="RSI14",

            category="MOMENTUM",

            data_type="DECIMAL",

            description="RSI",

            created_at=datetime.now(UTC),

            updated_at=datetime.now(UTC),
        ),

    ]

    session.add_all(features)

    session.commit()

    return features


def create_mapper(session):

    repository = FeatureDefinitionRepository(session)

    cache = FeatureIdCache(repository)

    return FeatureValueMapper(cache)


def test_mapper_creates_feature_values():

    session = create_session()

    features = seed_features(session)

    mapper = create_mapper(session)

    values = {

        "EMA20": Decimal("2450.10"),

        "RSI14": Decimal("62.35"),

    }

    result = mapper.map(

        instrument_id=1,

        trade_date=date(2026, 7, 16),

        values=values,

    )

    assert len(result) == 2


def test_mapper_assigns_feature_ids():

    session = create_session()

    features = seed_features(session)

    mapper = create_mapper(session)

    values = {

        "EMA20": Decimal("100"),

        "RSI14": Decimal("50"),

    }

    result = mapper.map(

        instrument_id=99,

        trade_date=date(2026, 1, 1),

        values=values,

    )

    ids = {

        value.feature_definition_id

        for value in result

    }

    expected = {

        features[0].id,

        features[1].id,

    }

    assert ids == expected


def test_mapper_assigns_instrument_id():

    session = create_session()

    seed_features(session)

    mapper = create_mapper(session)

    result = mapper.map(

        instrument_id=25,

        trade_date=date(2026, 1, 1),

        values={

            "EMA20": Decimal("150"),

        },

    )

    assert result[0].instrument_id == 25


def test_mapper_assigns_trade_date():

    session = create_session()

    seed_features(session)

    mapper = create_mapper(session)

    trade_date = date(2026, 5, 10)

    result = mapper.map(

        instrument_id=1,

        trade_date=trade_date,

        values={

            "EMA20": Decimal("100"),

        },

    )

    assert result[0].trade_date == trade_date


def test_mapper_assigns_decimal_value():

    session = create_session()

    seed_features(session)

    mapper = create_mapper(session)

    result = mapper.map(

        instrument_id=1,

        trade_date=date(2026, 1, 1),

        values={

            "EMA20": Decimal("123.45"),

        },

    )

    assert result[0].decimal_value == Decimal("123.45")


def test_mapper_unknown_feature_raises_key_error():

    session = create_session()

    seed_features(session)

    mapper = create_mapper(session)

    values = {

        "UNKNOWN": Decimal("10"),

    }

    try:

        mapper.map(

            instrument_id=1,

            trade_date=date(2026, 1, 1),

            values=values,

        )

        assert False

    except KeyError:

        assert True