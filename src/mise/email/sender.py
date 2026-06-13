"""Email sending functionality for Mise.

Uses SMTP for sending emails. Falls back to console output if SMTP
is not configured (useful for development).
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from mise.config import (
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD,
    EMAIL_FROM, EMAIL_VERIFICATION_REQUIRED,
)


def _smtp_configured() -> bool:
    """Check if SMTP is properly configured."""
    return bool(SMTP_USER and SMTP_PASSWORD)


def send_email(
    to: str,
    subject: str,
    body: str,
    html_body: Optional[str] = None,
) -> bool:
    """Send an email via SMTP.

    If SMTP is not configured, prints the email to console instead.
    Returns True if sent successfully (or printed to console).
    """
    if not _smtp_configured():
        # Development mode: just print the email
        print(f"\n{'='*60}")
        print(f"📧 EMAIL (development mode – SMTP not configured)")
        print(f"{'='*60}")
        print(f"To: {to}")
        print(f"From: {EMAIL_FROM}")
        print(f"Subject: {subject}")
        print(f"{'-'*60}")
        print(body)
        print(f"{'='*60}\n")
        return True

    msg = MIMEMultipart("alternative")
    msg["From"] = EMAIL_FROM
    msg["To"] = to
    msg["Subject"] = subject

    # Plain text part
    msg.attach(MIMEText(body, "plain"))

    # HTML part (optional)
    if html_body:
        msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(EMAIL_FROM, to, msg.as_string())
        return True
    except Exception as e:
        print(f"❌ Failed to send email to {to}: {e}")
        return False


def send_verification_email(to: str, code: str, username: str) -> bool:
    """Send a verification code email to a user.

    The email contains an 8-digit code that the user must enter
    to verify their email address.
    """
    subject = "Mise – Verify your email address"

    plain_body = f"""Hello {username},

Welcome to Mise! Please verify your email address by entering the following code:

    {code}

This code expires in 15 minutes.

If you didn't create an account on Mise, you can ignore this email.

– The Mise Team
"""

    html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <h2 style="color: #2d5016;">Welcome to Mise! 🍳</h2>
    <p>Hello {username},</p>
    <p>Please verify your email address by entering the following code:</p>
    <div style="background-color: #f0f7e6; border: 2px solid #2d5016; border-radius: 8px;
                padding: 16px; text-align: center; margin: 20px 0;">
        <span style="font-size: 32px; font-weight: bold; letter-spacing: 4px; color: #2d5016;">
            {code}
        </span>
    </div>
    <p style="color: #666; font-size: 14px;">This code expires in 15 minutes.</p>
    <p style="color: #999; font-size: 12px;">
        If you didn't create an account on Mise, you can ignore this email.
    </p>
    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
    <p style="color: #999; font-size: 12px;">– The Mise Team</p>
</body>
</html>
"""

    return send_email(to=to, subject=subject, body=plain_body, html_body=html_body)