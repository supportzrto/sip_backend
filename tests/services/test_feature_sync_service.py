from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.repositories.feature_definition_repository import (
    FeatureDefinitionRepository,
)
from app.services.feature_sync_service import FeatureSyncService
from app.feature_store.generator import FeatureGenerator


def create_session():

    engine = create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)

    return Session()


def test_sync_creates_all_features():

    session = create_session()

    service = FeatureSyncService(session)

    service.sync()

    repository = FeatureDefinitionRepository(session)

    features = repository.list_all()

    registry = FeatureGenerator().generate()

    assert len(features) == len(registry.all())

    database_names = {
        feature.name
        for feature in features
    }

    registry_names = {
        feature.name
        for feature in registry.all()
    }

    assert database_names == registry_names


def test_sync_is_idempotent():

    session = create_session()

    service = FeatureSyncService(session)

    service.sync()

    service.sync()

    repository = FeatureDefinitionRepository(session)

    features = repository.list_all()

    registry = FeatureGenerator().generate()

    assert len(features) == len(registry.all())


def test_sync_can_find_inserted_feature():

    session = create_session()

    service = FeatureSyncService(session)

    service.sync()

    repository = FeatureDefinitionRepository(session)

    ema20 = repository.get_by_name("EMA20")

    assert ema20 is not None

    assert ema20.name == "EMA20"