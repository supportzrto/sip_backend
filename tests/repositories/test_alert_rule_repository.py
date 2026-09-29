from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.models.alert_notification import AlertNotification
from app.models.alert_rule import AlertRule
from app.models.instrument import Instrument
from app.models.user import User
from app.repositories.alert_rule_repository import AlertRuleRepository


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


def create_instrument(session, symbol="RELIANCE"):

    instrument = Instrument(
        symbol=symbol,
        company_name=f"{symbol} Ltd",
        exchange="NSE",
        instrument_type="EQ",
        isin=f"INE{symbol}01018"[:12],
        provider="NSE",
        provider_token=symbol,
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    session.add(instrument)
    session.commit()

    return instrument


def test_create_and_list_for_user():

    session = create_session()
    user = create_user(session)
    repository = AlertRuleRepository(session)

    repository.create(
        AlertRule(
            user_id=user.id,
            name="Breakouts",
            strategy_key="breakout",
        )
    )
    repository.commit()

    rules = repository.list_for_user(user.id)

    assert len(rules) == 1
    assert rules[0].name == "Breakouts"
    assert rules[0].is_active is True
    assert rules[0].last_matched_symbols == []


def test_get_by_id_scoped_to_owner():

    session = create_session()
    owner = create_user(session, email="owner@example.com")
    other = create_user(session, email="other@example.com")
    repository = AlertRuleRepository(session)

    rule = repository.create(
        AlertRule(
            user_id=owner.id,
            name="Breakouts",
            strategy_key="breakout",
        )
    )
    repository.commit()

    assert repository.get_by_id(rule.id, user_id=owner.id) is not None
    assert repository.get_by_id(rule.id, user_id=other.id) is None
    assert repository.get_by_id(rule.id) is not None  # unscoped


def test_list_active_only_returns_active_rules():

    session = create_session()
    user = create_user(session)
    repository = AlertRuleRepository(session)

    repository.create(
        AlertRule(
            user_id=user.id,
            name="Active rule",
            strategy_key="breakout",
            is_active=True,
        )
    )
    repository.create(
        AlertRule(
            user_id=user.id,
            name="Paused rule",
            strategy_key="breakdown",
            is_active=False,
        )
    )
    repository.commit()

    active = repository.list_active()

    assert [rule.name for rule in active] == ["Active rule"]


def test_create_notifications_and_list_recent_for_user():

    session = create_session()
    user = create_user(session)
    instrument = create_instrument(session)
    repository = AlertRuleRepository(session)

    rule = repository.create(
        AlertRule(
            user_id=user.id,
            name="Breakouts",
            strategy_key="breakout",
        )
    )
    repository.commit()

    repository.create_notifications(
        [
            AlertNotification(
                alert_rule_id=rule.id,
                instrument_id=instrument.id,
                symbol=instrument.symbol,
                reasons=["close crossed above 20-day high"],
            )
        ]
    )
    repository.commit()

    notifications = repository.list_recent_notifications_for_user(
        user.id,
    )

    assert len(notifications) == 1
    assert notifications[0].symbol == instrument.symbol
    assert notifications[0].reasons == [
        "close crossed above 20-day high",
    ]


def test_delete_rule_cascades_to_notifications():

    session = create_session()
    user = create_user(session)
    instrument = create_instrument(session)
    repository = AlertRuleRepository(session)

    rule = repository.create(
        AlertRule(
            user_id=user.id,
            name="Breakouts",
            strategy_key="breakout",
        )
    )
    repository.commit()

    repository.create_notifications(
        [
            AlertNotification(
                alert_rule_id=rule.id,
                instrument_id=instrument.id,
                symbol=instrument.symbol,
                reasons=["reason"],
            )
        ]
    )
    repository.commit()

    repository.delete(rule)
    repository.commit()

    assert repository.list_recent_notifications_for_user(user.id) == []