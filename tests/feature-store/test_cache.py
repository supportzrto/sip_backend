from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.feature_store.cache import FeatureIdCache
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

            name="EMA50",

            category="TREND",

            data_type="DECIMAL",

            description="50 EMA",

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


def test_cache_size():

    session = create_session()

    seed_features(session)

    repository = FeatureDefinitionRepository(session)

    cache = FeatureIdCache(repository)

    assert cache.size() == 3


def test_cache_get_id():

    session = create_session()

    features = seed_features(session)

    repository = FeatureDefinitionRepository(session)

    cache = FeatureIdCache(repository)

    assert cache.get_id("EMA20") == features[0].id

    assert cache.get_id("EMA50") == features[1].id

    assert cache.get_id("RSI14") == features[2].id


def test_cache_exists():

    session = create_session()

    seed_features(session)

    repository = FeatureDefinitionRepository(session)

    cache = FeatureIdCache(repository)

    assert cache.exists("EMA20")

    assert cache.exists("EMA50")

    assert cache.exists("RSI14")


def test_cache_missing_feature():

    session = create_session()

    seed_features(session)

    repository = FeatureDefinitionRepository(session)

    cache = FeatureIdCache(repository)

    assert cache.exists("XYZ") is False


def test_cache_unknown_feature_raises():

    session = create_session()

    seed_features(session)

    repository = FeatureDefinitionRepository(session)

    cache = FeatureIdCache(repository)

    with pytest.raises(KeyError):

        cache.get_id("XYZ")