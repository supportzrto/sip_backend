"""
Transactional email delivery.

In production, set SMTP_HOST (and the other SMTP_* settings) so
emails are actually delivered via a real SMTP relay. In development,
when SMTP_HOST is left empty, send_email() falls back to logging the
message -- including whatever link/token it contains -- at INFO
level instead of raising. This keeps flows like forgot-password
usable locally without requiring real mail credentials, while still
exercising the exact same call path a real send would use.
"""

import logging
import smtplib
from email.message import EmailMessage

from app.config.settings import settings

logger = logging.getLogger(__name__)


class EmailDeliveryError(Exception):
    """
    Raised when an email fails to send via a configured SMTP server.
    Not raised when SMTP isn't configured at all -- that case logs
    and returns instead (see send_email).
    """


def send_email(
    *,
    to: str,
    subject: str,
    text_body: str,
    html_body: str | None = None,
) -> None:
    """
    Send a single email.

    Falls back to logging the message instead of sending it when no
    SMTP host is configured. Raises EmailDeliveryError if SMTP *is*
    configured but the send itself fails (auth failure, connection
    refused, etc.) -- callers decide whether that should fail their
    request or just be logged and swallowed.
    """

    if not settings.SMTP_HOST:
        logger.info(
            "SMTP not configured -- logging email instead of sending.\n"
            "To: %s\nSubject: %s\n\n%s",
            to,
            subject,
            text_body,
        )
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    message["To"] = to
    message.set_content(text_body)

    if html_body:
        message.add_alternative(html_body, subtype="html")

    try:
        with smtplib.SMTP(
            settings.SMTP_HOST,
            settings.SMTP_PORT,
            timeout=10,
        ) as smtp:

            if settings.SMTP_USE_TLS:
                smtp.starttls()

            if settings.SMTP_USERNAME:
                smtp.login(
                    settings.SMTP_USERNAME,
                    settings.SMTP_PASSWORD,
                )

            smtp.send_message(message)

    except (smtplib.SMTPException, OSError) as exc:

        logger.error(
            "Failed to send email to %s: %s",
            to,
            exc,
        )

        raise EmailDeliveryError(
            f"Failed to send email to {to}"
        ) from exc


def send_password_reset_email(
    *,
    to: str,
    full_name: str,
    reset_link: str,
) -> None:
    """
    Send a "reset your password" email containing the given link.
    The link's token and expiry are the caller's responsibility --
    this only formats and sends the message.
    """

    subject = "Reset your Stock Intelligence Platform password"

    text_body = (
        f"Hi {full_name},\n\n"
        "We received a request to reset your password. Click the "
        "link below to choose a new one. This link expires in 15 "
        "minutes.\n\n"
        f"{reset_link}\n\n"
        "If you didn't request this, you can safely ignore this "
        "email -- your password won't be changed.\n"
    )

    html_body = (
        f"<p>Hi {full_name},</p>"
        "<p>We received a request to reset your password. Click the "
        "link below to choose a new one. This link expires in "
        "15 minutes.</p>"
        f'<p><a href="{reset_link}">{reset_link}</a></p>'
        "<p>If you didn't request this, you can safely ignore this "
        "email -- your password won't be changed.</p>"
    )

    send_email(
        to=to,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
    )


def send_alert_email(
    *,
    to: str,
    full_name: str,
    alert_name: str,
    matches: list[tuple[str, list[str]]],
) -> None:
    """
    Notify a user that their alert rule found new matches.

    `matches` is a list of (symbol, reasons) pairs -- kept as plain
    tuples rather than importing a scanner type here, so this stays
    a generic, low-level email module with no dependency on the
    scanner package.
    """

    subject = (
        f"[{alert_name}] {len(matches)} new match"
        f"{'es' if len(matches) != 1 else ''}"
    )

    match_lines_text = "\n".join(
        f"- {symbol}: {'; '.join(reasons)}"
        for symbol, reasons in matches
    )

    match_lines_html = "".join(
        f"<li><strong>{symbol}</strong>: {'; '.join(reasons)}</li>"
        for symbol, reasons in matches
    )

    text_body = (
        f"Hi {full_name},\n\n"
        f"Your alert \"{alert_name}\" just found new matches:\n\n"
        f"{match_lines_text}\n\n"
        "You're getting this because you set up this alert on the "
        "Stock Intelligence Platform.\n"
    )

    html_body = (
        f"<p>Hi {full_name},</p>"
        f'<p>Your alert "{alert_name}" just found new matches:</p>'
        f"<ul>{match_lines_html}</ul>"
        "<p>You're getting this because you set up this alert on "
        "the Stock Intelligence Platform.</p>"
    )

    send_email(
        to=to,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
    )