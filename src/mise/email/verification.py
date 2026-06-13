"""Email verification code management.

Handles generating, storing, validating, and expiring verification codes.
Codes are 8-digit numeric strings, valid for 15 minutes.
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from mise.config import EMAIL_VERIFICATION_REQUIRED
from mise.db.database import SessionLocal
from mise.db.models import EmailVerification, User
from mise.email.sender import send_verification_email


CODE_LENGTH = 8
CODE_EXPIRY_MINUTES = 15


def _generate_code() -> str:
    """Generate a cryptographically secure 8-digit verification code."""
    return "".join([str(secrets.randbelow(10)) for _ in range(CODE_LENGTH)])


def create_verification_code(user_id: int, email: str, username: str) -> str:
    """Create a new verification code for a user and send it via email.

    Invalidates any previous unused codes for this user first.

    Returns the generated code (useful for testing/development).
    """
    session = SessionLocal()
    try:
        # Invalidate any previous unused codes for this user
        session.query(EmailVerification).filter(
            EmailVerification.user_id == user_id,
            EmailVerification.is_used.is_(False)
        ).update({"is_used": True})

        # Generate new code
        code = _generate_code()
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=CODE_EXPIRY_MINUTES)

        verification = EmailVerification(
            user_id=user_id,
            code=code,
            email=email,
            is_used=False,
            created_at=now,
            expires_at=expires_at,
        )
        session.add(verification)
        session.commit()

        # Send the verification email
        send_verification_email(to=email, code=code, username=username)

        return code
    finally:
        session.close()


def verify_code(user_id: int, code: str) -> tuple[bool, str]:
    """Verify a code submitted by a user.

    Returns (success, message).
    On success, also marks the user's is_verified flag as True.
    """
    session = SessionLocal()
    try:
        now = datetime.now(timezone.utc)

        # Find the verification entry
        verification = session.query(EmailVerification).filter(
            EmailVerification.user_id == user_id,
            EmailVerification.code == code,
            EmailVerification.is_used.is_(False)
        ).first()

        if verification is None:
            return False, "Invalid verification code."

        # Check if expired
        if verification.expires_at < now:
            return False, "Verification code has expired. Please request a new one."

        # Mark code as used
        verification.is_used = True

        # Mark user as verified
        user = session.query(User).filter(User.id == user_id).first()
        if user is None:
            return False, "User not found."

        user.is_verified = True
        session.commit()

        return True, "Email verified successfully!"
    finally:
        session.close()


def resend_verification(user_id: int) -> tuple[bool, str]:
    """Resend a verification code to the user's email.

    Returns (success, message).
    """
    session = SessionLocal()
    try:
        user = session.query(User).filter(User.id == user_id).first()
        if user is None:
            return False, "User not found."

        if user.is_verified:
            return False, "Email is already verified."

        # Create and send a new code
        create_verification_code(user.id, user.email, user.username)
        return True, f"Verification code sent to {user.email}."
    finally:
        session.close()


def is_verification_required() -> bool:
    """Check if email verification is required based on config."""
    return EMAIL_VERIFICATION_REQUIRED