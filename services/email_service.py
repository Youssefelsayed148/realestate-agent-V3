# services/email_service.py
from __future__ import annotations

import os
from typing import Optional

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


class EmailSendError(RuntimeError):
    pass


def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    *,
    from_email: Optional[str] = None,
    reply_to: Optional[str] = None,
) -> str:
    """
    Returns provider message id if available, else empty string.
    """
    api_key = os.getenv("SENDGRID_API_KEY")
    if not api_key:
        raise EmailSendError("Missing SENDGRID_API_KEY")

    from_email = from_email or os.getenv("EMAIL_FROM")
    if not from_email:
        raise EmailSendError("Missing EMAIL_FROM")

    msg = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject=subject,
        html_content=html_content,
    )
    if reply_to:
        msg.reply_to = reply_to

    sg = SendGridAPIClient(api_key)
    resp = sg.send(msg)

    # SendGrid status codes are typically 202 for accepted
    if resp.status_code >= 400:
        raise EmailSendError(f"SendGrid error status={resp.status_code}")

    # SendGrid may include message id in headers depending on config
    # We'll store something stable if present, else empty.
    message_id = ""
    try:
        message_id = resp.headers.get("X-Message-Id") or resp.headers.get("X-Message-ID") or ""
    except Exception:
        pass
    return message_id
