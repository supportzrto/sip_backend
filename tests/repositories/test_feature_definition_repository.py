from datetime import datetime,UTC

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
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


def test_create_feature_definition():

    session = create_session()

    repository = FeatureDefinitionRepository(
        session
    )

    feature = FeatureDefinition(

        name="EMA20",

        category="TREND",

        data_type="DECIMAL",

        description="20 EMA",

        created_at=datetime.now(UTC),

        updated_at=datetime.now(UTC),
    )

    repository.create(feature)

    session.commit()

    saved = repository.get_by_name(
        "EMA20"
    )

    assert saved is not None

    assert saved.name == "EMA20"

    assert saved.category == "TREND"


def test_get_by_name_returns_none():

    session = create_session()

    repository = FeatureDefinitionRepository(
        session
    )

    feature = repository.get_by_name(
        "UNKNOWN"
    )

    assert feature is None


def test_list_all():

    session = create_session()

    repository = FeatureDefinitionRepository(
        session
    )

    repository.create(

        FeatureDefinition(

            name="EMA20",

            category="TREND",

            data_type="DECIMAL",

            description="20 EMA",

            created_at=datetime.now(UTC),

            updated_at=datetime.now(UTC),
        )

    )

    repository.create(

        FeatureDefinition(

            name="EMA50",

            category="TREND",

            data_type="DECIMAL",

            description="50 EMA",

            created_at=datetime.now(UTC),

            updated_at=datetime.now(UTC),
        )

    )

    session.commit()

    features = repository.list_all()

    assert len(features) == 2

    names = {
        feature.name
        for feature in features
    }

    assert names == {
        "EMA20",
        "EMA50",
    }


def test_delete_feature_definition():

    session = create_session()

    repository = FeatureDefinitionRepository(
        session
    )

    feature = FeatureDefinition(

        name="RSI14",

        category="MOMENTUM",

        data_type="DECIMAL",

        description="RSI",

        created_at=datetime.now(UTC),

        updated_at=datetime.now(UTC),
    )

    repository.create(feature)

    session.commit()

    repository.delete(feature)

    session.commit()

    deleted = repository.get_by_name(
        "RSI14"
    )

    assert deleted is None