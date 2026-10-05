"""Outgoing email (password reset). Falls back to logging when SMTP isn't configured."""

import asyncio
import logging
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings

log = logging.getLogger(__name__)


def _send(message: EmailMessage) -> None:
    settings = get_settings()
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
        if settings.smtp_starttls:
            smtp.starttls()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)


async def send_password_reset(email: str, token: str) -> None:
    settings = get_settings()
    if not settings.smtp_host:
        # Dev fallback: no mail server, so the code goes to the server console.
        log.warning(
            "SMTP_HOST is not set; password reset email NOT sent. Reset code for %s (valid %d min): %s",
            email, settings.password_reset_expire_minutes, token,
        )
        return
    message = EmailMessage()
    message["Subject"] = "Robot Chess password reset"
    message["From"] = settings.smtp_from
    message["To"] = email
    message.set_content(
        "Someone asked to reset the password for your Robot Chess account.\n\n"
        f"Reset code: {token}\n\n"
        "In the app, tap \"Forgot password?\" > \"I have a reset code\" and paste it.\n"
        f"The code works once and expires in {settings.password_reset_expire_minutes} minutes.\n"
        "If this wasn't you, ignore this email; your password is unchanged."
    )
    try:
        await asyncio.to_thread(_send, message)
    except (OSError, smtplib.SMTPException):
        log.exception("Could not send the password reset email to %s", email)
