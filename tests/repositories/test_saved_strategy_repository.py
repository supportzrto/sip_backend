from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.models.saved_strategy import SavedStrategy
from app.models.user import User
from app.repositories.saved_strategy_repository import (
    SavedStrategyRepository,
)


def create_session():

    engine = create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)

    return Session()


def create_user(session, email="jane@example.com"):

    user = User(
        full_name="Jane Doe",
        email=email,
        password_hash="not-a-real-hash",
    )

    session.add(user)
    session.commit()

    return user


SAMPLE_EXPRESSION = {
    "operator": "AND",
    "children": [
        {"left": "RSI14", "operator": "<", "right": "30"},
    ],
}


def test_create_and_list_for_user():

    session = create_session()
    user = create_user(session)
    repository = SavedStrategyRepository(session)

    repository.create(
        SavedStrategy(
            user_id=user.id,
            name="My Custom Setup",
            expression=SAMPLE_EXPRESSION,
        )
    )
    repository.commit()

    strategies = repository.list_for_user(user.id)

    assert len(strategies) == 1
    assert strategies[0].name == "My Custom Setup"
    assert strategies[0].expression == SAMPLE_EXPRESSION


def test_get_by_id_scoped_to_owner():

    session = create_session()
    owner = create_user(session, email="owner@example.com")
    other = create_user(session, email="other@example.com")
    repository = SavedStrategyRepository(session)

    strategy = repository.create(
        SavedStrategy(
            user_id=owner.id,
            name="My Custom Setup",
            expression=SAMPLE_EXPRESSION,
        )
    )
    repository.commit()

    assert repository.get_by_id(strategy.id, user_id=owner.id) is not None
    assert repository.get_by_id(strategy.id, user_id=other.id) is None
    assert repository.get_by_id(strategy.id) is not None  # unscoped


def test_duplicate_name_for_same_user_is_rejected_at_db_level():

    session = create_session()
    user = create_user(session)
    repository = SavedStrategyRepository(session)

    repository.create(
        SavedStrategy(
            user_id=user.id,
            name="My Custom Setup",
            expression=SAMPLE_EXPRESSION,
        )
    )
    repository.commit()

    with pytest.raises(IntegrityError):
        repository.create(
            SavedStrategy(
                user_id=user.id,
                name="My Custom Setup",
                expression=SAMPLE_EXPRESSION,
            )
        )


def test_delete():

    session = create_session()
    user = create_user(session)
    repository = SavedStrategyRepository(session)

    strategy = repository.create(
        SavedStrategy(
            user_id=user.id,
            name="My Custom Setup",
            expression=SAMPLE_EXPRESSION,
        )
    )
    repository.commit()

    repository.delete(strategy)
    repository.commit()

    assert repository.list_for_user(user.id) == []