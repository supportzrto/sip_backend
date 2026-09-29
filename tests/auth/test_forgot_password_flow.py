from urllib.parse import parse_qs, urlparse

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.auth import service as auth_service_module
from app.auth.security import hash_password
from app.auth.service import AuthService
from app.database.base import Base
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User


def create_session():

    engine = create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)

    return Session()


def create_user(session, email="jane@example.com"):

    user = User(
        full_name="Jane Doe",
        email=email,
        password_hash=hash_password("Original-Password-1"),
    )

    session.add(user)
    session.commit()
    session.refresh(user)

    return user


def _extract_token(reset_link: str) -> str:

    query = parse_qs(urlparse(reset_link).query)

    return query["token"][0]


def test_forgot_password_sends_email_with_working_reset_link(monkeypatch):

    session = create_session()
    user = create_user(session)

    captured = {}

    def _fake_send_password_reset_email(*, to, full_name, reset_link):
        captured["to"] = to
        captured["full_name"] = full_name
        captured["reset_link"] = reset_link

    monkeypatch.setattr(
        auth_service_module,
        "send_password_reset_email",
        _fake_send_password_reset_email,
    )

    service = AuthService(session)

    service.forgot_password(email=user.email)

    # Email was sent to the right address with the user's name.
    assert captured["to"] == "jane@example.com"
    assert captured["full_name"] == "Jane Doe"

    # A token was actually persisted.
    stored = session.scalar(select(PasswordResetToken))
    assert stored is not None
    assert stored.user_id == user.id
    assert stored.used is False

    # The link handed to the email function contains a token that
    # genuinely resets the password end-to-end.
    raw_token = _extract_token(captured["reset_link"])

    service.reset_password(
        token=raw_token,
        new_password="Brand-New-Password-2",
    )

    session.refresh(user)

    from app.auth.security import verify_password

    assert verify_password("Brand-New-Password-2", user.password_hash)


def test_forgot_password_does_not_send_email_for_unknown_address(monkeypatch):

    session = create_session()

    calls = []

    monkeypatch.setattr(
        auth_service_module,
        "send_password_reset_email",
        lambda **kwargs: calls.append(kwargs),
    )

    service = AuthService(session)

    # Should not raise, and should not reveal whether the account
    # exists by sending (or not sending) differently.
    service.forgot_password(email="nobody@example.com")

    assert calls == []
    assert session.scalar(select(PasswordResetToken)) is None


def test_forgot_password_succeeds_even_if_email_delivery_fails(monkeypatch):
    """
    A down SMTP server shouldn't break the forgot-password request --
    the token is already safely persisted, and the caller only ever
    gets the same generic response either way.
    """

    session = create_session()
    user = create_user(session)

    def _raise(**kwargs):
        raise auth_service_module.EmailDeliveryError("smtp is down")

    monkeypatch.setattr(
        auth_service_module,
        "send_password_reset_email",
        _raise,
    )

    service = AuthService(session)

    # Must not raise.
    service.forgot_password(email=user.email)

    # The token was still persisted, so the user isn't locked out of
    # resetting once delivery is fixed / they retry.
    stored = session.scalar(select(PasswordResetToken))
    assert stored is not None
    assert stored.user_id == user.id