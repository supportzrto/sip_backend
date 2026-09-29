import pytest

from app.core import email as email_module
from app.core.email import (
    EmailDeliveryError,
    send_email,
    send_password_reset_email,
)


def test_send_email_logs_instead_of_sending_when_smtp_not_configured(
    monkeypatch,
    caplog,
):
    """
    With no SMTP_HOST set (the default), send_email should not try
    to open a network connection at all -- it should just log the
    message and return.
    """

    monkeypatch.setattr(
        email_module.settings,
        "SMTP_HOST",
        "",
    )

    def _fail_if_called(*args, **kwargs):
        raise AssertionError(
            "smtplib.SMTP should not be constructed when "
            "SMTP_HOST is empty."
        )

    monkeypatch.setattr(
        email_module.smtplib,
        "SMTP",
        _fail_if_called,
    )

    with caplog.at_level("INFO"):
        send_email(
            to="user@example.com",
            subject="Test subject",
            text_body="the reset link is https://example.com/reset?token=abc",
        )

    assert "user@example.com" in caplog.text
    assert "the reset link is https://example.com/reset?token=abc" in caplog.text


class _FakeSMTP:
    """
    Minimal stand-in for smtplib.SMTP as a context manager, recording
    what would have been sent so tests can assert on it without any
    real network I/O.
    """

    instances: list["_FakeSMTP"] = []

    def __init__(self, host, port, timeout=None):
        self.host = host
        self.port = port
        self.started_tls = False
        self.login_args = None
        self.sent_messages = []
        _FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def starttls(self):
        self.started_tls = True

    def login(self, username, password):
        self.login_args = (username, password)

    def send_message(self, message):
        self.sent_messages.append(message)


def test_send_email_sends_via_smtp_when_configured(monkeypatch):

    _FakeSMTP.instances = []

    monkeypatch.setattr(email_module.settings, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(email_module.settings, "SMTP_PORT", 587)
    monkeypatch.setattr(email_module.settings, "SMTP_USE_TLS", True)
    monkeypatch.setattr(email_module.settings, "SMTP_USERNAME", "apikey")
    monkeypatch.setattr(email_module.settings, "SMTP_PASSWORD", "secret")
    monkeypatch.setattr(email_module.smtplib, "SMTP", _FakeSMTP)

    send_email(
        to="user@example.com",
        subject="Test subject",
        text_body="hello",
        html_body="<p>hello</p>",
    )

    assert len(_FakeSMTP.instances) == 1

    smtp = _FakeSMTP.instances[0]

    assert smtp.started_tls is True
    assert smtp.login_args == ("apikey", "secret")
    assert len(smtp.sent_messages) == 1
    assert smtp.sent_messages[0]["To"] == "user@example.com"
    assert smtp.sent_messages[0]["Subject"] == "Test subject"


def test_send_email_raises_email_delivery_error_on_smtp_failure(monkeypatch):

    monkeypatch.setattr(email_module.settings, "SMTP_HOST", "smtp.example.com")

    class _BoomSMTP:

        def __init__(self, *args, **kwargs):
            raise ConnectionRefusedError("nope")

    monkeypatch.setattr(email_module.smtplib, "SMTP", _BoomSMTP)

    with pytest.raises(EmailDeliveryError):
        send_email(
            to="user@example.com",
            subject="Test subject",
            text_body="hello",
        )


def test_send_password_reset_email_includes_link_in_body(monkeypatch):

    captured = {}

    def _fake_send_email(*, to, subject, text_body, html_body=None):
        captured["to"] = to
        captured["subject"] = subject
        captured["text_body"] = text_body
        captured["html_body"] = html_body

    monkeypatch.setattr(email_module, "send_email", _fake_send_email)

    send_password_reset_email(
        to="jane@example.com",
        full_name="Jane Doe",
        reset_link="https://app.example.com/reset-password?token=abc123",
    )

    assert captured["to"] == "jane@example.com"
    assert "Jane Doe" in captured["text_body"]
    assert (
        "https://app.example.com/reset-password?token=abc123"
        in captured["text_body"]
    )
    assert (
        "https://app.example.com/reset-password?token=abc123"
        in captured["html_body"]
    )