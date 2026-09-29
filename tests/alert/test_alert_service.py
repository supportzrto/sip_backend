from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth.repository import UserRepository
from app.database.base import Base
from app.models.alert_rule import AlertRule
from app.models.instrument import Instrument
from app.models.user import User
from app.models.watchlist import Watchlist
from app.models.watchlist_item import WatchlistItem
from app.repositories.alert_rule_repository import AlertRuleRepository
from app.repositories.instrument_repository import InstrumentRepository
from app.repositories.saved_strategy_repository import (
    SavedStrategyRepository,
)
from app.repositories.watchlist_repository import WatchlistRepository
from app.scanner.schemas import ScanResult
from app.services import alert_service as alert_service_module
from app.services.alert_service import AlertService


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


def create_instrument(session, symbol):

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


class _FakeScannerService:
    """
    Stands in for ScannerService -- AlertService only ever calls
    .scan(), so a real feature-store setup isn't needed to test
    AlertService's own diff/notify logic in isolation.
    """

    def __init__(self, results_by_call):
        # A list of ScanResult lists, one per call, returned in
        # order -- lets a test simulate "day 1 matches X", "day 2
        # matches X and Y", etc.
        self._results_by_call = list(results_by_call)
        self.calls = []

    def scan(self, request, user_id=None, symbols=None):
        self.calls.append({"user_id": user_id, "symbols": symbols})
        return self._results_by_call.pop(0)


def build_service(session, scanner_service):

    return AlertService(
        scanner_service=scanner_service,
        alert_rule_repository=AlertRuleRepository(session),
        watchlist_repository=WatchlistRepository(session),
        instrument_repository=InstrumentRepository(session),
        saved_strategy_repository=SavedStrategyRepository(session),
        user_repository=UserRepository(session),
    )


def test_run_rule_notifies_only_on_first_match(monkeypatch):

    session = create_session()
    user = create_user(session)
    create_instrument(session, "RELIANCE")

    alert_repository = AlertRuleRepository(session)
    rule = alert_repository.create(
        AlertRule(
            user_id=user.id,
            name="Breakouts",
            strategy_key="breakout",
        )
    )
    alert_repository.commit()

    sent_emails = []

    monkeypatch.setattr(
        alert_service_module,
        "send_alert_email",
        lambda **kwargs: sent_emails.append(kwargs),
    )

    scanner = _FakeScannerService(
        results_by_call=[
            [ScanResult(symbol="RELIANCE", reasons=["broke out"])],
        ],
    )
    service = build_service(session, scanner)

    newly_matched = service.run_rule(rule)

    assert [r.symbol for r in newly_matched] == ["RELIANCE"]
    assert len(sent_emails) == 1
    assert sent_emails[0]["to"] == "jane@example.com"
    assert sent_emails[0]["matches"] == [
        ("RELIANCE", ["broke out"]),
    ]

    session.refresh(rule)
    assert rule.last_matched_symbols == ["RELIANCE"]
    assert rule.last_checked_at is not None


def test_run_rule_does_not_renotify_a_symbol_that_keeps_matching(
    monkeypatch,
):

    session = create_session()
    user = create_user(session)
    create_instrument(session, "RELIANCE")

    alert_repository = AlertRuleRepository(session)
    rule = alert_repository.create(
        AlertRule(
            user_id=user.id,
            name="Breakouts",
            strategy_key="breakout",
            last_matched_symbols=["RELIANCE"],  # matched last run too
        )
    )
    alert_repository.commit()

    sent_emails = []

    monkeypatch.setattr(
        alert_service_module,
        "send_alert_email",
        lambda **kwargs: sent_emails.append(kwargs),
    )

    scanner = _FakeScannerService(
        results_by_call=[
            [ScanResult(symbol="RELIANCE", reasons=["still breaking out"])],
        ],
    )
    service = build_service(session, scanner)

    newly_matched = service.run_rule(rule)

    # Still matching, but NOT new -- no email, nothing returned.
    assert newly_matched == []
    assert sent_emails == []

    session.refresh(rule)
    assert rule.last_matched_symbols == ["RELIANCE"]


def test_run_rule_notifies_again_after_a_symbol_drops_out_and_returns(
    monkeypatch,
):

    session = create_session()
    user = create_user(session)
    create_instrument(session, "RELIANCE")

    alert_repository = AlertRuleRepository(session)
    rule = alert_repository.create(
        AlertRule(
            user_id=user.id,
            name="Breakouts",
            strategy_key="breakout",
        )
    )
    alert_repository.commit()

    sent_emails = []

    monkeypatch.setattr(
        alert_service_module,
        "send_alert_email",
        lambda **kwargs: sent_emails.append(kwargs),
    )

    scanner = _FakeScannerService(
        results_by_call=[
            [ScanResult(symbol="RELIANCE", reasons=["broke out"])],  # run 1
            [],  # run 2: dropped out
            [ScanResult(symbol="RELIANCE", reasons=["broke out again"])],  # run 3
        ],
    )
    service = build_service(session, scanner)

    service.run_rule(rule)
    session.refresh(rule)
    assert rule.last_matched_symbols == ["RELIANCE"]

    service.run_rule(rule)
    session.refresh(rule)
    assert rule.last_matched_symbols == []

    third_run_matches = service.run_rule(rule)

    assert [r.symbol for r in third_run_matches] == ["RELIANCE"]
    assert len(sent_emails) == 2  # once for run 1, once for run 3


def test_run_rule_scopes_scan_to_watchlist_symbols(monkeypatch):

    session = create_session()
    user = create_user(session)
    reliance = create_instrument(session, "RELIANCE")
    create_instrument(session, "TCS")

    watchlist_repository = WatchlistRepository(session)
    watchlist = watchlist_repository.create(
        Watchlist(user_id=user.id, name="My Longs"),
    )
    watchlist_repository.add_item(
        WatchlistItem(
            watchlist_id=watchlist.id,
            instrument_id=reliance.id,
        )
    )
    watchlist_repository.commit()

    alert_repository = AlertRuleRepository(session)
    rule = alert_repository.create(
        AlertRule(
            user_id=user.id,
            name="Breakouts",
            strategy_key="breakout",
            watchlist_id=watchlist.id,
        )
    )
    alert_repository.commit()

    monkeypatch.setattr(
        alert_service_module,
        "send_alert_email",
        lambda **kwargs: None,
    )

    scanner = _FakeScannerService(results_by_call=[[]])
    service = build_service(session, scanner)

    service.run_rule(rule)

    assert scanner.calls == [
        {"user_id": user.id, "symbols": ["RELIANCE"]},
    ]


def test_run_rule_skips_scan_for_empty_watchlist(monkeypatch):

    session = create_session()
    user = create_user(session)

    watchlist_repository = WatchlistRepository(session)
    watchlist = watchlist_repository.create(
        Watchlist(user_id=user.id, name="Empty"),
    )
    watchlist_repository.commit()

    alert_repository = AlertRuleRepository(session)
    rule = alert_repository.create(
        AlertRule(
            user_id=user.id,
            name="Breakouts",
            strategy_key="breakout",
            watchlist_id=watchlist.id,
        )
    )
    alert_repository.commit()

    scanner = _FakeScannerService(results_by_call=[])  # .scan() must not be called
    service = build_service(session, scanner)

    result = service.run_rule(rule)

    assert result == []
    assert scanner.calls == []

    session.refresh(rule)
    assert rule.last_checked_at is not None


def test_run_rule_email_failure_does_not_lose_the_recorded_match(
    monkeypatch,
):

    session = create_session()
    user = create_user(session)
    create_instrument(session, "RELIANCE")

    alert_repository = AlertRuleRepository(session)
    rule = alert_repository.create(
        AlertRule(
            user_id=user.id,
            name="Breakouts",
            strategy_key="breakout",
        )
    )
    alert_repository.commit()

    def _raise(**kwargs):
        raise alert_service_module.EmailDeliveryError("smtp is down")

    monkeypatch.setattr(
        alert_service_module,
        "send_alert_email",
        _raise,
    )

    scanner = _FakeScannerService(
        results_by_call=[
            [ScanResult(symbol="RELIANCE", reasons=["broke out"])],
        ],
    )
    service = build_service(session, scanner)

    # Must not raise.
    newly_matched = service.run_rule(rule)

    assert [r.symbol for r in newly_matched] == ["RELIANCE"]

    session.refresh(rule)
    assert rule.last_matched_symbols == ["RELIANCE"]

    notifications = alert_repository.list_recent_notifications_for_user(
        user.id,
    )
    assert len(notifications) == 1
    assert notifications[0].symbol == "RELIANCE"


def test_run_all_active_skips_a_failing_rule_and_continues(monkeypatch):

    session = create_session()
    user = create_user(session)
    create_instrument(session, "RELIANCE")
    create_instrument(session, "TCS")

    alert_repository = AlertRuleRepository(session)

    broken_rule = alert_repository.create(
        AlertRule(
            user_id=user.id,
            name="Broken",
            strategy_key="not-a-real-strategy",
        )
    )
    healthy_rule = alert_repository.create(
        AlertRule(
            user_id=user.id,
            name="Healthy",
            strategy_key="breakout",
        )
    )
    alert_repository.commit()

    monkeypatch.setattr(
        alert_service_module,
        "send_alert_email",
        lambda **kwargs: None,
    )

    scanner = _FakeScannerService(
        results_by_call=[
            [ScanResult(symbol="TCS", reasons=["broke out"])],
        ],
    )
    service = build_service(session, scanner)

    # Must not raise even though broken_rule has an unknown strategy.
    service.run_all_active()

    session.refresh(healthy_rule)
    assert healthy_rule.last_matched_symbols == ["TCS"]


def test_run_rule_uses_saved_strategy_expression(monkeypatch):

    from app.models.saved_strategy import SavedStrategy
    from app.scanner.schemas import ScanExpression

    session = create_session()
    user = create_user(session)
    create_instrument(session, "RELIANCE")

    saved_strategy_repository = SavedStrategyRepository(session)
    saved_strategy = saved_strategy_repository.create(
        SavedStrategy(
            user_id=user.id,
            name="My Custom Setup",
            expression={
                "operator": "AND",
                "children": [
                    {
                        "left": "RSI14",
                        "operator": "<",
                        "right": "30",
                    },
                ],
            },
        )
    )
    saved_strategy_repository.commit()

    alert_repository = AlertRuleRepository(session)
    rule = alert_repository.create(
        AlertRule(
            user_id=user.id,
            name="Custom Alert",
            saved_strategy_id=saved_strategy.id,
        )
    )
    alert_repository.commit()

    monkeypatch.setattr(
        alert_service_module,
        "send_alert_email",
        lambda **kwargs: None,
    )

    scanner = _FakeScannerService(results_by_call=[[]])
    service = build_service(session, scanner)

    service.run_rule(rule)

    # The scan request built from the saved strategy's stored
    # expression actually reached ScannerService.scan().
    assert len(scanner.calls) == 1


def test_run_rule_skips_when_saved_strategy_was_deleted_out_from_under_it(
    monkeypatch,
):
    """
    saved_strategy_id is ON DELETE CASCADE, so in practice the rule
    is deleted along with its strategy -- this covers the defensive
    fallback for a dangling reference regardless.
    """

    session = create_session()
    user = create_user(session)

    alert_repository = AlertRuleRepository(session)
    rule = AlertRule(
        user_id=user.id,
        name="Custom Alert",
        saved_strategy_id=999,  # no such saved strategy
    )
    alert_repository.create(rule)
    alert_repository.commit()

    scanner = _FakeScannerService(results_by_call=[])  # must not be called
    service = build_service(session, scanner)

    result = service.run_rule(rule)

    assert result == []
    assert scanner.calls == []